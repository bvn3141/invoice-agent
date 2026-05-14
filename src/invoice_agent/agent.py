"""Agent entry point: iterate the inbox, run a Claude Agent SDK query per PDF.

Each invoice is processed in an isolated query so:
- failures on one invoice don't contaminate the rest,
- the demo video can show a clean per-invoice rhythm,
- cost is bounded per invoice instead of accumulating context.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows consoles so tool-call streaming with non-ASCII chars
# (vendor names with umlauts, etc.) doesn't crash the run with cp1252 errors.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover — older Pythons
        pass

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    query,
)

from invoice_agent.outputs import OUTPUT_DIR, PROCESSED_XLSX, REVIEW_DIR, reset_outputs
from invoice_agent.prompts import SYSTEM_PROMPT
from invoice_agent.tools import TOOL_NAMES, build_mcp_server

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INBOX = PROJECT_ROOT / "demo_inputs" / "inbox"


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"invoice": build_mcp_server()},
        allowed_tools=["Read", *TOOL_NAMES],
        permission_mode="bypassPermissions",
        max_turns=18,
        cwd=str(PROJECT_ROOT),
    )


async def _drive_query(pdf_path: Path, options: ClaudeAgentOptions, verbose: bool) -> tuple[list[str], str, float | None]:
    """Single attempt at processing one invoice. May raise on transport errors."""
    fmt = pdf_path.suffix.lower().lstrip(".") or "pdf"
    user_prompt = (
        f"Process the invoice at the absolute path:\n  {pdf_path.as_posix()}\n\n"
        f"Note: this file is a .{fmt} input — handle accordingly. "
        f"Use the workflow exactly as instructed. End with the single RESULT line."
    )

    tool_calls: list[str] = []
    last_text = ""
    cost: float | None = None

    async for message in query(prompt=user_prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    last_text = block.text.strip() or last_text
                    if verbose and block.text.strip():
                        print(f"      | {block.text.strip()[:140]}")
                elif isinstance(block, ToolUseBlock):
                    tool_calls.append(block.name)
                    if verbose:
                        print(f"      > {block.name}({_summarize_input(block.input)})")
                elif isinstance(block, ToolResultBlock):
                    if verbose:
                        print(f"      < (result)")
        elif isinstance(message, ResultMessage):
            cost = getattr(message, "total_cost_usd", None)

    return tool_calls, last_text, cost


async def _process_one(pdf_path: Path, options: ClaudeAgentOptions, verbose: bool) -> dict:
    """Process one PDF with one retry on transient SDK errors.

    The Claude Agent SDK occasionally raises `Claude Code returned an error
    result: success` mid-batch (suspected rate-limit / session-end protocol
    quirk). Retrying once after a short pause clears it in practice.
    """
    started = time.perf_counter()
    error: str | None = None
    tool_calls: list[str] = []
    last_text = ""
    cost: float | None = None

    for attempt in (1, 2):
        try:
            tool_calls, last_text, cost = await _drive_query(pdf_path, options, verbose)
            error = None
            break
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            if attempt == 1:
                if verbose:
                    print(f"      ! transient error, retrying once: {error}")
                await asyncio.sleep(2.5)
            else:
                if verbose:
                    print(f"      ! failed after retry: {error}")

    return {
        "filename": pdf_path.name,
        "tool_calls": tool_calls,
        "last_text": last_text,
        "elapsed_s": round(time.perf_counter() - started, 1),
        "cost_usd": cost,
        "error": error,
    }


def _summarize_input(inp: dict | None, width: int = 70) -> str:
    if not inp:
        return ""
    parts = []
    for k, v in inp.items():
        s = str(v)
        if len(s) > 40:
            s = s[:37] + "…"
        parts.append(f"{k}={s}")
    out = ", ".join(parts)
    return out if len(out) <= width else out[: width - 1] + "…"


# ─── Human-readable narration helpers ─────────────────────────────────────────

_REASON_LABEL_DE = {
    "math_error": "Mathematik-Fehler",
    "duplicate": "Duplikat",
    "unknown_vendor": "Neuer Lieferant (nicht in Stammdaten)",
    "currency_mismatch": "Fremde Währung",
    "extraction_failed": "Extraktion gescheitert",
    "other": "Sonstiges",
}


def _parse_result_line(text: str) -> dict:
    """Parse the agent's final 'RESULT: …' line into structured pieces."""
    line = ""
    for cand in text.splitlines():
        if cand.strip().startswith("RESULT:"):
            line = cand.strip()
            break
    if not line:
        return {}
    body = line[len("RESULT:"):].strip()
    parts = [p.strip() for p in body.split("|")]
    keys = ["status", "invoice_no", "vendor", "amount", "reason"]
    return {k: (parts[i] if i < len(parts) else "") for i, k in enumerate(keys)}


def _read_review_for(filename: str) -> dict | None:
    """Locate and parse the review JSON for one invoice."""
    if not REVIEW_DIR.exists():
        return None
    stem = Path(filename).stem
    for jp in sorted(REVIEW_DIR.iterdir()):
        if jp.suffix == ".json" and jp.stem.startswith(stem):
            try:
                return json.loads(jp.read_text(encoding="utf-8"))
            except Exception:
                return None
    return None


def _print_intro_banner(invoices: list[Path]) -> None:
    n_pdf = sum(1 for p in invoices if p.suffix.lower() == ".pdf")
    n_html = sum(1 for p in invoices if p.suffix.lower() == ".html")
    parts = []
    if n_pdf:
        parts.append(f"{n_pdf} PDF" + ("s" if n_pdf != 1 else ""))
    if n_html:
        parts.append(f"{n_html} HTML-Bestellbestätigung" + ("en" if n_html != 1 else ""))
    formats = ", ".join(parts) if parts else "—"

    line = "=" * 64
    print(line)
    print(" Invoice Agent — Inbox-Verarbeitung gestartet")
    print(line)
    print(f"  Hallo. Ich habe {len(invoices)} neue Rechnung(en) in der Inbox gefunden")
    print(f"  und beginne jetzt mit der Bearbeitung.")
    print()
    print(f"  Formate:  {formats}")
    print(f"  Pro Rechnung lese ich die Datei, extrahiere alle Felder,")
    print(f"  prüfe Vendor, Mathematik und Duplikate und entscheide:")
    print(f"    -> in Excel buchen (PROCESSED), oder")
    print(f"    -> zur manuellen Prüfung markieren (REVIEW)")
    print()
    print(f"  Ergebnisse landen in:")
    print(f"    output/processed.xlsx   (alles was sauber durchläuft)")
    print(f"    output/review/*.json    (alles was du dir ansehen solltest)")
    print(line)
    print()


def _human_comment(result_parts: dict) -> str:
    """One short German comment line summarizing what the agent decided."""
    if result_parts.get("status") == "PROCESSED":
        amount = result_parts.get("amount", "")
        return f"=> In Excel gebucht ({amount})." if amount else "=> In Excel gebucht."
    if result_parts.get("status") == "REVIEW":
        reason_raw = result_parts.get("reason", "").strip()
        if not reason_raw:
            return "=> Zur Prüfung markiert."
        rtype = reason_raw.split()[0].rstrip(":,")
        label = _REASON_LABEL_DE.get(rtype, reason_raw)
        return f"=> Zur Prüfung markiert: {label}."
    return ""


def _print_final_report(summaries: list[dict]) -> None:
    processed = [s for s in summaries if "PROCESSED" in s["last_text"]]
    reviews = [s for s in summaries if "REVIEW" in s["last_text"]]
    errors = [s for s in summaries if s["error"]]

    line = "=" * 64
    print()
    print(line)
    print(" Abschluss-Bericht für die Buchhaltung")
    print(line)
    print()
    print(f"  Von {len(summaries)} Eingangsrechnungen sind:")
    print(f"    {len(processed):>2}  in der Excel gelandet (output/processed.xlsx)")
    print(f"    {len(reviews):>2}  zur manuellen Prüfung markiert (output/review/)")
    if errors:
        print(f"    {len(errors):>2}  technisch fehlgeschlagen (siehe Log oben)")
    print()

    if processed:
        print(f"  OK Sauber durchgelaufen ({len(processed)}):")
        for s in processed:
            p = _parse_result_line(s["last_text"])
            vendor = p.get("vendor", "?")[:30]
            amount = p.get("amount", "")
            print(f"      - {s['filename']:20s} {vendor:30s} {amount}")
        print()

    if reviews:
        print(f"  !! Bitte ansehen — NICHT in der Excel ({len(reviews)}):")
        print()
        for i, s in enumerate(reviews, 1):
            review = _read_review_for(s["filename"])
            p = _parse_result_line(s["last_text"])
            vendor = p.get("vendor", "?")
            print(f"   {i}. {s['filename']}  ({vendor})")
            if review and "reason" in review:
                rtype = review["reason"].get("type", "?")
                label = _REASON_LABEL_DE.get(rtype, rtype)
                explanation = review["reason"].get("explanation", "").strip()
                print(f"      Problem: {label}")
                if explanation:
                    for chunk in _wrap(explanation, width=58):
                        print(f"      Warum:   {chunk}" if chunk == _wrap(explanation, width=58)[0] else f"               {chunk}")
            else:
                print(f"      Problem: {p.get('reason', 'unklar')}")
            print()

    print(f"  Tipp: Öffne output/processed.xlsx zur Übersicht. Die JSON-")
    print(f"  Dateien unter output/review/ enthalten die volle Begründung")
    print(f"  inkl. extrahierter Rechnungs-Felder.")
    print(line)


def _wrap(text: str, *, width: int = 60) -> list[str]:
    """Tiny word-wrap so explanation lines fit in the report column."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        if not current:
            current = w
        elif len(current) + 1 + len(w) <= width:
            current += " " + w
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines or [""]


async def run(inbox: Path, *, limit: int | None, fresh: bool, verbose: bool) -> dict:
    invoices: list[Path] = sorted(
        [*inbox.glob("*.pdf"), *inbox.glob("*.html")],
        key=lambda p: p.stem,
    )
    if limit is not None:
        invoices = invoices[:limit]

    if not invoices:
        raise SystemExit(
            f"No invoices (.pdf/.html) in {inbox}. "
            f"Run `python -m data_generator.generate` first."
        )

    if fresh:
        reset_outputs()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _print_intro_banner(invoices)

    options = _build_options()

    overall_started = time.perf_counter()
    summaries: list[dict] = []
    for i, pdf in enumerate(invoices, 1):
        print(f"[{i:3d}/{len(invoices)}] {pdf.name}")
        summary = await _process_one(pdf, options, verbose)
        summaries.append(summary)
        if summary["error"]:
            print(f"           ERROR after retry: {summary['error']}  ({summary['elapsed_s']}s)")
        else:
            result_line = summary["last_text"].splitlines()[-1] if summary["last_text"] else "<no result line>"
            print(f"           {result_line}  ({summary['elapsed_s']}s, {len(summary['tool_calls'])} tool calls)")
            comment = _human_comment(_parse_result_line(summary["last_text"]))
            if comment:
                print(f"           {comment}")

    overall_elapsed = time.perf_counter() - overall_started

    n_processed = sum(1 for s in summaries if not s["error"] and "PROCESSED" in s["last_text"])
    n_review = sum(1 for s in summaries if not s["error"] and "REVIEW" in s["last_text"])
    n_errors = sum(1 for s in summaries if s["error"])
    n_unknown = len(summaries) - n_processed - n_review - n_errors

    print("\n-- Run summary -------------------------------------")
    print(f"  total invoices:      {len(invoices)}")
    print(f"  processed:           {n_processed}")
    print(f"  flagged for review:  {n_review}")
    if n_errors:
        print(f"  errors (failed):     {n_errors}")
    if n_unknown:
        print(f"  ambiguous outputs:   {n_unknown}")
    print(f"  elapsed:             {overall_elapsed:.1f}s")
    print(f"  processed.xlsx:      {PROCESSED_XLSX}")
    print(f"  review folder:       {REVIEW_DIR}")

    _print_final_report(summaries)

    return {
        "summaries": summaries,
        "n_processed": n_processed,
        "n_review": n_review,
        "n_errors": n_errors,
        "elapsed_s": round(overall_elapsed, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the invoice agent over the inbox.")
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX, help="folder with invoice PDFs/HTML files")
    parser.add_argument("--limit", type=int, default=None, help="process at most N invoices")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="wipe output/processed.xlsx and output/review/ before running",
    )
    parser.add_argument("--verbose", action="store_true", help="stream tool calls and intermediate reasoning")
    args = parser.parse_args()

    asyncio.run(run(args.inbox, limit=args.limit, fresh=args.fresh, verbose=args.verbose))


if __name__ == "__main__":
    main()
