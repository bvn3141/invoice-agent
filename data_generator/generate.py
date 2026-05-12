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

    if not inject_edge_cases or n < 8:
        return plan

    candidate_idx = list(range(n))
    rng.shuffle(candidate_idx)
    take = iter(candidate_idx)

    # Duplicate: pick two slots, force them to share the same vendor + invoice number.
    a, b = next(take), next(take)
    forced_no = f"INV-2026-DUP-{rng.randint(1000, 9999)}"
    plan[a]["force_invoice_no"] = forced_no
    plan[b]["force_invoice_no"] = forced_no
    plan[b]["vendor"] = plan[a]["vendor"]
    plan[a]["edge_cases"].append("duplicate")
    plan[b]["edge_cases"].append("duplicate")

    # Math error (two invoices)
    for _ in range(2):
        plan[next(take)]["edge_cases"].append("math_error")

    # Unknown vendor (two invoices)
    for unknown in rng.sample(UNKNOWN_VENDORS, k=2):
        idx = next(take)
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
    scan_indices = set(rng.sample(range(n), k=min(scan_count, n)))

    manifest: list[dict] = []
    for item in plan:
        idx = item["idx"]
        vendor: Vendor = item["vendor"]
        data = templates.build_data(vendor, rng)
        if item["force_invoice_no"]:
            data["invoice_no"] = item["force_invoice_no"]
        if "math_error" in item["edge_cases"]:
            _inject_math_error(data, rng)

        pdf_path = output_dir / f"invoice_{idx:03d}.pdf"
        is_scan = idx in scan_indices
        if is_scan:
            distortions.render_scan(data, pdf_path, rng)
        else:
            templates.render_clean(data, pdf_path)

        entry = _serialize_data(data)
        entry["filename"] = pdf_path.name
        entry["scan"] = is_scan
        entry["edge_cases"] = item["edge_cases"]
        manifest.append(entry)

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "n": n,
        "scans": len(scan_indices),
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
    print(f"  Edge cases injected: {result['edge_cases']}")
    print(f"  Manifest: {result['manifest_path']}")


if __name__ == "__main__":
    main()
