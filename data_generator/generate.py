"""CLI: generate synthetic invoice PDFs into `demo_inputs/inbox/`.

Usage:
    python -m data_generator.generate --n 30 --seed 42

Writes:
- N invoice PDFs into the inbox folder (a mix of clean and scan-look)
- `demo_inputs/manifest.json` with ground-truth fields per invoice, plus
  flags for any deliberately-injected edge cases (duplicate invoice number,
  math error, unknown vendor, currency mismatch).

The manifest is used in Phase 4 to verify the agent's extraction. It is not
read by the agent itself — the agent only sees the PDFs.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict
from pathlib import Path

from data_generator import distortions, templates
from data_generator.fixtures import (
    UNKNOWN_VENDORS,
    Vendor,
    load_vendors,
    vendors_by_template,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "demo_inputs" / "inbox"
DEFAULT_MANIFEST = PROJECT_ROOT / "demo_inputs" / "manifest.json"


def _serialize_data(data: dict) -> dict:
    """Convert non-JSON-friendly objects in the ground-truth dict."""
    out = dict(data)
    out["vendor"] = asdict(data["vendor"])
    out["invoice_date"] = data["invoice_date"].isoformat()
    out["due_date"] = data["due_date"].isoformat()
    return out


def _inject_math_error(data: dict, rng: random.Random) -> None:
    """Break the math invariant: brutto != netto + ust by a small but obvious delta."""
    delta = round(rng.uniform(2.0, 9.0), 2)
    direction = rng.choice([-1, 1])
    data["brutto"] = round(data["brutto"] + direction * delta, 2)


def _make_plan(n: int, vendors: list[Vendor], inject_edge_cases: bool, rng: random.Random) -> list[dict]:
    by_template = vendors_by_template(vendors)
    template_keys = list(by_template.keys())
    plan: list[dict] = []
    for i in range(n):
        tpl = rng.choice(template_keys)
        vendor = rng.choice(by_template[tpl])
        plan.append({"idx": i, "vendor": vendor, "edge_cases": [], "force_invoice_no": None})

    if not inject_edge_cases or n < 4:
        return plan

    # Scale edge-case counts with N so a 10-invoice demo still hits all four types.
    n_math = max(1, n // 10)
    n_unknown = max(1, n // 10)

    candidate_idx = list(range(n))
    rng.shuffle(candidate_idx)

    # Duplicate pair: pick two slots at least 3 apart so the second hit isn't
    # adjacent to the first — gives the demo viewer a moment to register the catch.
    a = candidate_idx.pop(0)
    b_pos = next((i for i, idx in enumerate(candidate_idx) if abs(idx - a) >= 3), 0)
    b = candidate_idx.pop(b_pos)
    forced_no = f"INV-2026-DUP-{rng.randint(1000, 9999)}"
    plan[a]["force_invoice_no"] = forced_no
    plan[b]["force_invoice_no"] = forced_no
    plan[b]["vendor"] = plan[a]["vendor"]
    plan[a]["edge_cases"].append("duplicate")
    plan[b]["edge_cases"].append("duplicate")

    # Math errors
    for _ in range(n_math):
        if not candidate_idx:
            break
        plan[candidate_idx.pop(0)]["edge_cases"].append("math_error")

    # Unknown vendors — prefer the CHF Helvetia vendor first so a single
    # invoice covers both "unknown vendor" and "non-EUR currency" in the demo.
    pool = list(UNKNOWN_VENDORS)
    rng.shuffle(pool)
    chf_vendor = next((v for v in UNKNOWN_VENDORS if v.default_currency == "CHF"), None)
    if chf_vendor and chf_vendor in pool:
        pool.remove(chf_vendor)
        pool.insert(0, chf_vendor)
    for unknown in pool[:n_unknown]:
        if not candidate_idx:
            break
        idx = candidate_idx.pop(0)
        plan[idx]["vendor"] = unknown
        plan[idx]["edge_cases"].append("unknown_vendor")

    return plan


def generate(
    n: int,
    output_dir: Path,
    manifest_path: Path,
    scan_ratio: float,
    seed: int,
    inject_edge_cases: bool,
) -> dict:
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    vendors = load_vendors()
    plan = _make_plan(n, vendors, inject_edge_cases, rng)

    scan_count = int(round(n * scan_ratio))
    # Stack at least one scan onto a math-error invoice so the demo can show
    # "vision pipeline + math check both fire on the same document".
    math_error_idxs = [item["idx"] for item in plan if "math_error" in item["edge_cases"]]
    scan_indices: set[int] = set()
    if math_error_idxs and scan_count > 0:
        scan_indices.add(math_error_idxs[0])
    remaining_pool = [i for i in range(n) if i not in scan_indices]
    needed = max(0, min(scan_count, n) - len(scan_indices))
    if needed:
        scan_indices.update(rng.sample(remaining_pool, k=min(needed, len(remaining_pool))))

    # Pick one HTML-only slot: a clean webshop invoice (no scan, no edge case).
    # Webshops realistically send HTML order confirmations instead of PDFs, so
    # this exercises the agent's multi-format input handling.
    html_idx: int | None = None
    if inject_edge_cases and n >= 4:
        for item in plan:
            i = item["idx"]
            if (
                item["vendor"].template == "webshop"
                and not item["edge_cases"]
                and i not in scan_indices
            ):
                html_idx = i
                break

    manifest: list[dict] = []
    for item in plan:
        idx = item["idx"]
        vendor: Vendor = item["vendor"]
        data = templates.build_data(vendor, rng)
        if item["force_invoice_no"]:
            data["invoice_no"] = item["force_invoice_no"]
        if "math_error" in item["edge_cases"]:
            _inject_math_error(data, rng)

        is_scan = idx in scan_indices
        is_html = idx == html_idx

        if is_html:
            file_path = output_dir / f"invoice_{idx:03d}.html"
            templates.render_html_order(data, file_path)
        elif is_scan:
            file_path = output_dir / f"invoice_{idx:03d}.pdf"
            distortions.render_scan(data, file_path, rng)
        else:
            file_path = output_dir / f"invoice_{idx:03d}.pdf"
            templates.render_clean(data, file_path)

        entry = _serialize_data(data)
        entry["filename"] = file_path.name
        entry["scan"] = is_scan
        entry["html"] = is_html
        entry["edge_cases"] = item["edge_cases"]
        manifest.append(entry)

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "n": n,
        "scans": len(scan_indices),
        "html": sum(1 for m in manifest if m.get("html")),
        "edge_cases": sum(1 for m in manifest if m["edge_cases"]),
        "manifest_path": str(manifest_path),
        "output_dir": str(output_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic invoice PDFs.")
    parser.add_argument("--n", type=int, default=30, help="number of invoices to generate")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output directory")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="path for ground-truth manifest")
    parser.add_argument("--scan-ratio", type=float, default=0.25, help="fraction rendered as scans")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument(
        "--no-edge-cases",
        dest="edge_cases",
        action="store_false",
        help="disable injection of duplicate / math-error / unknown-vendor cases",
    )
    parser.set_defaults(edge_cases=True)
    args = parser.parse_args()

    result = generate(
        n=args.n,
        output_dir=args.output,
        manifest_path=args.manifest,
        scan_ratio=args.scan_ratio,
        seed=args.seed,
        inject_edge_cases=args.edge_cases,
    )

    print(f"Generated {result['n']} invoices into {result['output_dir']}")
    print(f"  Scans: {result['scans']}")
    print(f"  HTML order confirmations: {result['html']}")
    print(f"  Edge cases injected: {result['edge_cases']}")
    print(f"  Manifest: {result['manifest_path']}")


if __name__ == "__main__":
    main()
