"""MCP tools that the agent uses to validate, categorise, and persist invoices.

Each tool is a small async handler with a typed input schema. We keep the
business logic here and pass through to `outputs.py` for the file-side
effects. The tools are bundled into a single in-process MCP server via
`build_mcp_server()` and registered on the agent's options.

Naming convention: when wired to the SDK with server name "invoice", Claude
sees these tools as `mcp__invoice__<tool_name>`.
"""

from __future__ import annotations

import json
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool

from invoice_agent.outputs import (
    append_processed_row,
    existing_invoice_numbers,
    write_review_entry,
)
from invoice_agent.schemas import Invoice, LineItem, ReviewReason

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENDORS_PATH = PROJECT_ROOT / "data" / "vendors.json"

# Closed-set categories the agent can pick from. Curated so the Excel column
# stays clean for downstream filtering / pivot use.
EXPENSE_CATEGORIES = [
    "Bürobedarf",
    "Software/Hardware",
    "Fachliteratur",
    "Bewirtung",
    "Werkzeug",
    "Beratung",
    "Reisekosten",
    "Sonstiges",
]

VENDOR_FUZZY_THRESHOLD = 0.78


def _ok(text: str, **extra) -> dict:
    payload = {"content": [{"type": "text", "text": text}]}
    if extra:
        payload["content"][0]["text"] += "\n\n" + json.dumps(extra, ensure_ascii=False)
    return payload


def _err(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "is_error": True}


def _load_vendors() -> list[dict]:
    return json.loads(VENDORS_PATH.read_text(encoding="utf-8"))


def _fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _parse_invoice(args: dict) -> Invoice:
    """Build an Invoice model from a flexible dict that the agent provides."""
    line_items = [
        LineItem(**li)
        for li in args.get("line_items", [])
    ]
    return Invoice(
        filename=args["filename"],
        invoice_no=args["invoice_no"],
        vendor_name=args["vendor_name"],
        vendor_id=args.get("vendor_id"),
        invoice_date=date.fromisoformat(args["invoice_date"]),
        due_date=date.fromisoformat(args["due_date"]) if args.get("due_date") else None,
        currency=args["currency"],
        netto=float(args["netto"]),
        ust=float(args["ust"]),
        brutto=float(args["brutto"]),
        ust_rate=float(args.get("ust_rate", 0.0)),
        category=args.get("category"),
        line_items=line_items,
    )


# ─── Tools ────────────────────────────────────────────────────────────────────


@tool(
    "lookup_vendor",
    "Look up a vendor in the master records by name (fuzzy match). Returns "
    "vendor_id, default_category, default_currency, country, and iban if found. "
    "If the vendor is unknown, returns 'NOT FOUND' — that is an edge case worth "
    "flagging for review.",
    {"vendor_name": str},
)
async def lookup_vendor(args: dict) -> dict:
    query_name = args["vendor_name"].strip()
    if not query_name:
        return _err("lookup_vendor was called with an empty vendor_name.")

    vendors = _load_vendors()
    best = max(vendors, key=lambda v: _fuzzy_score(query_name, v["name"]))
    score = _fuzzy_score(query_name, best["name"])
    if score < VENDOR_FUZZY_THRESHOLD:
        return _ok(
            f"NOT FOUND. Best near-match was '{best['name']}' (score={score:.2f}), "
            f"which is below the {VENDOR_FUZZY_THRESHOLD:.2f} acceptance threshold. "
            f"Treat the vendor as unknown."
        )
    return _ok(
        f"FOUND vendor.",
        match_score=round(score, 3),
        vendor_id=best["id"],
        canonical_name=best["name"],
        country=best["country"],
        default_category=best["default_category"],
        default_currency=best["default_currency"],
        iban=best["iban"],
    )


@tool(
    "check_duplicate",
    "Check whether an invoice with this (invoice_no, vendor identifier) tuple "
    "has already been written to processed.xlsx. Use this before appending. "
    "Pass vendor_id if known, otherwise pass vendor_name as a fallback key.",
    {"invoice_no": str, "vendor_id_or_name": str},
)
async def check_duplicate(args: dict) -> dict:
    invoice_no = args["invoice_no"]
    key = args["vendor_id_or_name"]
    seen = existing_invoice_numbers()
    is_dup = (invoice_no, key) in seen or any(invoice_no == s[0] for s in seen)
    if is_dup:
        return _ok(
            f"DUPLICATE. invoice_no={invoice_no} already appears in processed.xlsx "
            f"for vendor key '{key}'. Flag for review with reason=duplicate; do NOT append."
        )
    return _ok(f"OK. invoice_no={invoice_no} is not in processed.xlsx yet — safe to append after other checks pass.")


@tool(
    "verify_math",
    "Verify that the invoice arithmetic is internally consistent: "
    "(a) netto + ust ≈ brutto (tolerance 0.02), and "
    "(b) netto * ust_rate ≈ ust (tolerance 0.02). "
    "Pass ust_rate as a decimal (e.g. 0.19 for 19%). For zero-VAT invoices, "
    "pass ust=0 and ust_rate=0.",
    {"netto": float, "ust": float, "brutto": float, "ust_rate": float},
)
async def verify_math(args: dict) -> dict:
    netto = float(args["netto"])
    ust = float(args["ust"])
    brutto = float(args["brutto"])
    rate = float(args["ust_rate"])

    total_check = abs(netto + ust - brutto)
    rate_check = abs(netto * rate - ust)

    problems = []
    if total_check > 0.02:
        problems.append(
            f"netto + ust = {netto + ust:.2f} but brutto = {brutto:.2f} (delta {total_check:.2f})"
        )
    if rate > 0 and rate_check > 0.02:
        problems.append(
            f"netto * rate = {netto * rate:.2f} but ust = {ust:.2f} (delta {rate_check:.2f})"
        )

    if problems:
        return _ok(
            "MATH ERROR. " + " | ".join(problems) + " — Flag for review with reason=math_error."
        )
    return _ok("OK. All arithmetic checks pass within tolerance.")


@tool(
    "categorize_expense",
    "Pick an expense category for the invoice. Choose from: "
    + ", ".join(EXPENSE_CATEGORIES)
    + ". If the vendor has a default_category from lookup_vendor, you may take "
    "that as a strong hint, but override it if the line items clearly point "
    "elsewhere. Returns the chosen category back to confirm.",
    {"category": str, "reason": str},
)
async def categorize_expense(args: dict) -> dict:
    category = args["category"]
    if category not in EXPENSE_CATEGORIES:
        return _err(
            f"'{category}' is not in the allowed category list. "
            f"Pick one of: {EXPENSE_CATEGORIES}"
        )
    return _ok(f"CATEGORY = {category}. Reason recorded: {args.get('reason', '')[:200]}")


@tool(
    "append_to_excel",
    "Persist a fully-validated invoice as a row in output/processed.xlsx. Call "
    "this ONLY after lookup_vendor, verify_math, and check_duplicate have all "
    "passed, AND categorize_expense has produced a category. Pass the invoice "
    "fields as a single object; line_items is optional but recommended.",
    {
        "filename": str,
        "invoice_no": str,
        "vendor_name": str,
        "vendor_id": str,
        "invoice_date": str,
        "due_date": str,
        "currency": str,
        "netto": float,
        "ust": float,
        "brutto": float,
        "ust_rate": float,
        "category": str,
    },
)
async def append_to_excel(args: dict) -> dict:
    try:
        invoice = _parse_invoice(args)
    except Exception as e:  # pragma: no cover — defensive: surface parse problems to the agent
        return _err(f"Could not parse invoice from args: {e}")
    append_processed_row(invoice)
    return _ok(
        f"APPENDED. {invoice.invoice_no} from {invoice.vendor_name} "
        f"({invoice.brutto:.2f} {invoice.currency}) is now in processed.xlsx."
    )


@tool(
    "flag_for_review",
    "Route an invoice to the review folder with a structured reason. Use this "
    "when ANY validation fails (math_error, duplicate, unknown_vendor) or when "
    "the extraction itself was ambiguous (extraction_failed). The 'type' must "
    "be one of: duplicate, math_error, unknown_vendor, currency_mismatch, "
    "extraction_failed, other. Provide a clear human-readable explanation.",
    {
        "filename": str,
        "invoice_no": str,
        "vendor_name": str,
        "invoice_date": str,
        "currency": str,
        "netto": float,
        "ust": float,
        "brutto": float,
        "reason_type": str,
        "reason_explanation": str,
    },
)
async def flag_for_review(args: dict) -> dict:
    try:
        invoice = Invoice(
            filename=args["filename"],
            invoice_no=args["invoice_no"],
            vendor_name=args["vendor_name"],
            invoice_date=date.fromisoformat(args["invoice_date"]),
            currency=args["currency"],
            netto=float(args["netto"]),
            ust=float(args["ust"]),
            brutto=float(args["brutto"]),
        )
        reason = ReviewReason(
            type=args["reason_type"],  # validated against Literal in pydantic
            explanation=args["reason_explanation"],
        )
    except Exception as e:
        return _err(f"Could not build review entry: {e}")
    path = write_review_entry(invoice, reason)
    return _ok(f"FLAGGED for review. Reason={reason.type}. Written to {path.name}.")


def build_mcp_server():
    """Bundle all tools into one in-process MCP server."""
    return create_sdk_mcp_server(
        name="invoice",
        version="0.1.0",
        tools=[
            lookup_vendor,
            check_duplicate,
            verify_math,
            categorize_expense,
            append_to_excel,
            flag_for_review,
        ],
    )


# Tool names as Claude will see them — useful for `allowed_tools`.
TOOL_NAMES = [
    "mcp__invoice__lookup_vendor",
    "mcp__invoice__check_duplicate",
    "mcp__invoice__verify_math",
    "mcp__invoice__categorize_expense",
    "mcp__invoice__append_to_excel",
    "mcp__invoice__flag_for_review",
]
