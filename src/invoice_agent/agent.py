"""Agent entry point: iterate the inbox, run a Claude Agent SDK query per PDF.

Each invoice is processed in an isolated query so:
- failures on one invoice don't contaminate the rest,
- the demo video can show a clean per-invoice rhythm,
- cost is bounded per invoice instead of accumulating context.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Iterable

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
    """Single attempt at processing one PDF. May raise on transport errors."""
    user_prompt = (
        f"Process the invoice at the absolute path:\n  {pdf_path.as_posix()}\n\n"
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


async def run(inbox: Path, *, limit: int | None, fresh: bool, verbose: bool) -> dict:
    pdfs: Iterable[Path] = sorted(inbox.glob("*.pdf"))
    if limit is not None:
        pdfs = list(pdfs)[:limit]
    pdfs = list(pdfs)

    if not pdfs:
        raise SystemExit(f"No PDFs in {inbox}. Run `python -m data_generator.generate` first.")

    if fresh:
        reset_outputs()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    options = _build_options()

    overall_started = time.perf_counter()
    summaries: list[dict] = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i:3d}/{len(pdfs)}] {pdf.name}")
        summary = await _process_one(pdf, options, verbose)
        summaries.append(summary)
        if summary["error"]:
            print(f"           ERROR after retry: {summary['error']}  ({summary['elapsed_s']}s)")
        else:
            result_line = summary["last_text"].splitlines()[-1] if summary["last_text"] else "<no result line>"
            print(f"           {result_line}  ({summary['elapsed_s']}s, {len(summary['tool_calls'])} tool calls)")

    overall_elapsed = time.perf_counter() - overall_started

    n_processed = sum(1 for s in summaries if not s["error"] and "PROCESSED" in s["last_text"])
    n_review = sum(1 for s in summaries if not s["error"] and "REVIEW" in s["last_text"])
    n_errors = sum(1 for s in summaries if s["error"])
    n_unknown = len(summaries) - n_processed - n_review - n_errors

    print("\n-- Run summary -------------------------------------")
    print(f"  total invoices:      {len(pdfs)}")
    print(f"  processed:           {n_processed}")
    print(f"  flagged for review:  {n_review}")
    if n_errors:
        print(f"  errors (failed):     {n_errors}")
    if n_unknown:
        print(f"  ambiguous outputs:   {n_unknown}")
    print(f"  elapsed:             {overall_elapsed:.1f}s")
    print(f"  processed.xlsx:      {PROCESSED_XLSX}")
    print(f"  review folder:       {REVIEW_DIR}")

    return {
        "summaries": summaries,
        "n_processed": n_processed,
        "n_review": n_review,
        "n_errors": n_errors,
        "elapsed_s": round(overall_elapsed, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the invoice agent over the inbox.")
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX, help="folder with invoice PDFs")
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
