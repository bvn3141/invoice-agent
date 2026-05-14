# Invoice Agent

An agentic invoice-processing showcase built on the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Drop a stack of synthetic invoice PDFs (or HTML order confirmations) into a folder; an agent reads them, extracts structured data, validates against vendor records, categorises expenses, and routes exceptions to a review folder — at around fifty seconds per invoice.

> **🎬 Demo video + full case study:** [benediktvennen.de/projects/invoice-agent](https://benediktvennen.de/projects/invoice-agent)

**Why this exists.** Office workers spend around 4.5 hours a week on tasks they themselves believe could be automated ([UiPath 2021 Office Worker Survey](https://www.uipath.com/newsroom/new-study-finds-majority-of-global-office-workers-crushed-by-repetitive-tasks)). Invoice processing — read document → enter data → categorise → file — is the canonical example. This project shows what an honest agentic workflow looks like for that problem: not a single LLM prompt, but a typed Pydantic tool loop with validation, deduplication, exception routing, and a sane review handoff for the edge cases.

**Cost note.** All model calls run through the Claude Pro plan via the Claude Agent SDK — no separate Anthropic API key, no per-token billing. The SDK reuses Claude Code's authentication.

See [`case-study.md`](case-study.md) for the long-form write-up.

## Quick start

Requires Python 3.11+, [Claude Code](https://docs.claude.com/en/docs/claude-code/quickstart) installed and authenticated, and a Claude Pro (or higher) subscription.

```bash
# 1. Install dependencies (creates a .venv via uv)
python -m uv sync

# 2. Generate a batch of synthetic invoices (10 files into demo_inputs/inbox/,
#    same configuration as the demo video on the portfolio page)
python -m uv run python -m data_generator.generate --n 10 --seed 42

# 3. Run the agent — processes the inbox, writes output/processed.xlsx + output/review/
python -m uv run python -m invoice_agent --fresh
```

Add `--verbose` to the agent run to stream each tool call as it happens.
Add `--limit N` to process only the first `N` invoices in the inbox (useful while iterating).
Bump `--n` on the generator for a larger batch (default is 30; the showcase uses 10 because every individual run is observable end-to-end in roughly eight minutes).

## What the agent does

For each PDF it finds in the inbox folder:

```
PDF
 │
 ▼
[Read]  ─── built-in: returns text-layer or page image (for scans)
 │
 ▼
extract  ─── agent parses invoice_no, vendor, dates, amounts, line items
 │
 ▼
[lookup_vendor]   ─── fuzzy-match against data/vendors.json
[verify_math]     ─── netto + tax ≈ brutto (within 0.02)
[check_duplicate] ─── against rows already in processed.xlsx
 │
 ▼
all three pass? ─── yes ──► [categorize_expense] ──► [append_to_excel]
                ─── no  ──► [flag_for_review] with structured reason
 │
 ▼
RESULT: PROCESSED | invoice_no | vendor | amount currency
RESULT: REVIEW    | invoice_no | vendor | amount currency | reason
```

Each domain tool is a small typed Python function bundled into an in-process MCP server. The agent decides which tool to call and when. The control flow is in the prompt and the model, not in the host script.

## Repository layout

```
invoice-agent/
├── src/invoice_agent/
│   ├── agent.py        # entry point: iterate inbox, one query per PDF
│   ├── tools.py        # six MCP tools + in-process server builder
│   ├── prompts.py      # system prompt (workflow + decision rules)
│   ├── schemas.py      # Pydantic models (Invoice, LineItem, ReviewReason)
│   └── outputs.py      # Excel writer, review folder router
├── data_generator/
│   ├── generate.py     # CLI: synthetic invoice batch with injected edge cases
│   ├── templates.py    # webshop_de, consulting_en, office_supplies_de layouts
│   ├── distortions.py  # PIL-rendered scan-look image-only PDFs
│   └── fixtures.py     # vendor master, Faker setup, product catalogues
├── data/
│   └── vendors.json    # vendor master records (15 vendors across 3 templates)
├── docs/
│   ├── architecture.svg
│   └── video_script.md
├── PROGRESS.md         # session-to-session progress log
├── case-study.md       # long-form write-up (mirrored on portfolio page)
└── pyproject.toml
```

## The injected edge cases

The generator does not just produce clean invoices. It deliberately injects the cases that hurt accounts payable in real operations, so the agent's value is observable. Counts below are for the showcase batch (`--n 10 --seed 42`); the generator scales these up roughly proportionally for larger `--n`.

| Edge case | Count (10-batch) | What should happen |
|---|---|---|
| Duplicate (same invoice no + vendor) | 2 (one pair) | First processed, second flagged with `duplicate` reason |
| Math error (netto + tax ≠ brutto) | 1 | Flagged with `math_error` reason |
| Unknown vendor (not in master records) | 1 | Flagged with `unknown_vendor` reason — short-circuits before currency would be checked, so an incidentally-CHF invoice is not flagged separately on currency |
| Scan-look (image-only, no text layer) | 2 (~20%) | Vision fallback kicks in; agent reads the image |
| HTML order confirmation (not a PDF) | 1 | Same workflow; the `Read` tool handles HTML transparently |

Re-run the generator with `--no-edge-cases` if you want a clean batch.

## Configuration

`pyproject.toml` declares all Python dependencies. `uv.lock` is committed so cloning the repo reproduces the exact dependency tree.

The agent runs in `permission_mode="bypassPermissions"` so tool calls are autonomous — appropriate for a showcase. For a production rollout, switching to `permission_mode="auto"` with explicit approval hooks on `append_to_excel` and `flag_for_review` is the obvious tighter setup.

The model used is whatever Claude Code's session default points at — typically Sonnet on a Pro plan. Override via `CLAUDE_MODEL` if you want to test a different one.

## Why this is not finished

See the *What this does not yet do* section in [`case-study.md`](case-study.md). Short version: this is a demo that proves the workflow shape. A production deployment would add audit logging, a payment-approval hook, a real accounting-system writer (DATEV / lexoffice / sevDesk), a vendor-onboarding flow, and a rate-limit-aware batcher for large queues.

## License

MIT. See [LICENSE](LICENSE).

## Credits

Built by Benedikt Vennen as part of an agentic-AI showcase series. The companion portfolio entry — with the embedded demo video and the case study rendered inline — is at [benediktvennen.de/projects/invoice-agent](https://benediktvennen.de/projects/invoice-agent).
