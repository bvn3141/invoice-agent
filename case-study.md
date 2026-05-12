# Invoice Agent — Case Study

The text intended for the portfolio project page. Written to mirror the voice
of the existing Fair Lending and Chocolate Credibility entries: declarative,
specific, no marketing language. Translated to JSX in Phase 6.

---

## The problem nobody is paid to solve well

Every office processes invoices. The work is the same in every industry:
open a PDF, read the fields, check the vendor, check the math, check that it
is not a duplicate of last month's, pick a category, type the relevant
numbers into a spreadsheet or accounting system. Each one takes between
three and eight minutes if everything is in order. A small business handling
a hundred invoices a month spends five to thirteen hours doing exactly this,
every month. UiPath's 2021 Office Worker Survey put the average global
office worker at four and a half hours a week on tasks they themselves
believed could be automated. Invoice handling was at the top of the list
then and remains there in 2026.

There is no skill in this work. It is also not something anyone is paid to
do well — it is the kind of task that gets done badly because it is boring,
and the badly-done version creates downstream problems: payments to wrong
vendors, missed early-payment discounts, the same invoice booked twice,
budget categories that nobody can audit later. The cost of a manual error is
$10 to $25 per invoice according to AppZen's 2025 AP benchmarks. The cost of
the time spent doing it correctly is roughly the same. Either way, money
walks out the door for work that should not require human attention.

## What "agentic" means, and what it does not

A workflow becomes agentic the moment the program stops following a fixed
script and starts deciding for itself which tool to use, in what order, and
how to handle the cases the script did not anticipate. That is the dividing
line between this project and a chatbot-with-extraction. A single
LLM call that returns a JSON object is not an agent. An agent is what
happens when a model can call functions, observe their results, and choose
its next move on that basis.

Concretely, the agent in this project executes the following loop for every
invoice it receives:

1. Read the PDF. If there is a text layer, parse it. If there is no text
   layer — the file is a scanned image — fall back to vision.
2. Extract a structured record: invoice number, vendor name, dates,
   currency, line items, totals, tax fields.
3. Call `lookup_vendor` against the master records, fuzzy-matched. If the
   vendor is not in the records, that is not necessarily wrong, but it is
   not the agent's call to decide.
4. Call `verify_math` to confirm the arithmetic is internally consistent.
   Tolerance two cents.
5. Call `check_duplicate` against the rows already in the processed
   spreadsheet. Same invoice number from the same vendor twice means
   something has gone wrong upstream.
6. Decide. If all three checks pass, call `categorize_expense` to pick a
   booking category from a closed set, then `append_to_excel`. If anything
   failed, call `flag_for_review` with the structured reason. Never both.
7. Emit one summary line so the operator running the batch can see at a
   glance what happened.

The decisions in step 6 are the part that justifies the word agent. The
model is not following a switch statement; it is deciding which of two
branches to take based on the typed return values of three independent
tools, and it is producing a human-readable explanation for the review
branch that includes the specific failure mode. A pure pipeline cannot do
this without being rewritten every time a new edge case appears. The agent
handles new edge cases by selecting a different combination of the same
tools.

## Architecture decisions

The agent runs on the Claude Agent SDK. Three reasons.

First, cost containment. The SDK reuses Claude Code's authentication and
billing model, which means a Claude Pro subscription covers all model
calls. No separate Anthropic API key, no per-token billing surprise. For a
portfolio project, this matters; for a small business piloting this kind of
workflow, it matters more.

Second, native tool use. The SDK accepts tools defined as decorated Python
functions with typed input schemas. Each tool runs in-process — no
inter-process communication overhead, no MCP server to spawn separately, no
Docker container around the agent. Six business-logic tools plus Claude
Code's built-in `Read` is the entire surface area.

Third, the SDK's tool routing matches the model the showcase wants to
demonstrate. Tools belong to a named MCP server (`invoice`), Claude sees
them as `mcp__invoice__verify_math` and so on, and the run loop streams
each tool call back to the controller. That stream is what the demo video
captures: the agent thinking, calling a tool, getting a result, deciding,
calling the next one. It is what makes the autonomy visible.

Inside the tools, validation is done in plain Python. Pydantic models
normalise the shape of records before they reach the spreadsheet writer.
Excel I/O goes through `openpyxl`. The review folder writes one JSON file
per flagged invoice with the structured reason — that file is the audit
trail. None of this is novel. The novelty is putting it behind an agent
that decides when to call which piece.

## Edge cases, deliberately built

The synthetic invoice generator does not produce thirty clean invoices and
call it done. It injects six specific edge cases on top of the clean set,
chosen because they are the ones that hurt accounts payable in real
operations:

- **Duplicates.** Two invoices share the same number from the same vendor.
  The agent must process the first normally and flag the second.
- **Math errors.** Two invoices have `netto + tax ≠ brutto` by a small but
  detectable delta. The agent must catch this without false positives on
  the legitimate cases.
- **Unknown vendors.** Two invoices come from companies that are not in
  the master records. The agent must recognise the absence rather than
  hallucinate a match.
- **Currency variance.** One of the unknown vendors invoices in CHF,
  another in USD. The currency field is extracted alongside everything
  else, and downstream systems care about the difference.

A quarter of the batch is also rendered as scan-look image-only PDFs with
slight rotation, JPEG compression artefacts, and gaussian noise. These
files have no text layer at all. The agent has to fall back to vision to
read them, which is exactly the failure mode that breaks naive
regex-and-PDF-parser pipelines in production.

## Results

The reference run processes the thirty-invoice batch in roughly twenty-five
minutes, with about fifty seconds per invoice on a Claude Pro plan. The
eight-invoice validation subset, which includes the first duplicate pair,
produced seven processed records and one flagged review. The duplicate was
detected on the second occurrence and routed correctly. The agent's review
note read:

> Invoice number INV-2026-DUP-6313 for vendor VND-006 (Schmidt Strategy
> Group GmbH) already exists in processed.xlsx. Vendor and math checks both
> passed, but this is a duplicate submission and must not be re-booked.

That sentence is what makes this useful in practice. A reviewer reading the
flagged JSON does not have to guess what the agent thought. The
justification is there, with the specific reference to the already-booked
record.

A second observation worth recording: the agent overrode a vendor's default
booking category in one case. The vendor BuchBar Versand is registered with
a default category of `Fachliteratur` (books), but the actual line items on
that invoice were coffee beans, a branded mug, and a desk organiser. The
agent re-categorised it as `Bürobedarf` (office supplies) and recorded the
reason. This is the kind of contextual judgement that justifies the
existence of the categorisation tool rather than a hard-coded
vendor-to-category map.

## What this does not yet do

The honest list. A real KMU deployment would require additional layers:

- An audit log that retains the agent's full reasoning trail, not just the
  summary, for compliance review. GoBD requires immutable storage of the
  reasoning in many German jurisdictions.
- A payment-approval workflow. Processing an invoice into a spreadsheet is
  not the same as authorising payment. A second human-in-the-loop step is
  appropriate for any amount above a configurable threshold.
- An integration with a real accounting system (DATEV, lexoffice,
  sevDesk). The Excel export is a deliberate showcase choice — it makes
  the data immediately legible — but production usage would write to the
  accounting system directly.
- A vendor master that supports onboarding new vendors mid-flow rather
  than only flagging unknowns. The current agent escalates; a more mature
  version would propose the new vendor record for human approval and
  proceed.
- Rate-limit-aware batching when handling hundreds of invoices at once.
  The current per-invoice query model is the right design for a fifty-item
  batch; it would need a different pattern at scale.

None of these are exotic. They are the gap between a demo that works and a
system in production. They are also where the engineering judgement
actually lives, and where this project would extend if a hiring company
asked for a version that could go live on Monday.

## Key numbers

```text
manual_processing_time_per_invoice  = 3–8 min  // industry baseline (UiPath, 2021)
agent_processing_time_per_invoice   ≈ 50 s     // Claude Pro, Sonnet-class model
duplicate_detection_rate            = 1/1      // the injected pair, second occurrence flagged
math_error_detection_tolerance      = 0.02     // both directions, currency-agnostic
unknown_vendor_threshold            = 0.78     // fuzzy-match acceptance score
vision_fallback_required            ≈ 25 %     // scan variants in the synthetic batch
allowed_categories                  = 8        // closed set, prevents free-text drift
tool_calls_per_invoice              = 5–7      // Read + 4–6 domain tools, deterministic
```

The point is not the percentages. The point is that every decision the
agent makes has a number behind it that can be tuned, audited, and
explained.
