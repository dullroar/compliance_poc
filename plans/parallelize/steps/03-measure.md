---
id: 03-measure
status: pending
depends_on: [01-provider-gates, 02-guard-thread-safety]
touches:
  - plans/parallelize/results.md
  - plans/parallelize/runs-anthropic.jsonl
  - usage/anthropic-api-ledger.jsonl
  - README.md
lane: measure
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R5, R6]
evidence: ""
---

# Ramp the width 2, 4, 8 on Anthropic, measure, and document it

Write for an agent with no chat history.

## Change

- Add an opt-in live timing (own environment variable, off by default) that runs the sample case at width 1, then 2, 4 and 8, one run each and stopping at the first width that errors for a reason other than cost, through the production batch path, and records wall time per phase, per-role latency, tokens, cache tokens and any 429. Preflight and reserve first; settle from usage.
- Write `results.md` (table by width, percentage change, rate-limit events, CPU burst note). Set the committed `remote_concurrency` to the highest clean width. If the domain-phase gain at that width is under 25%, say so.
- README: operator note for `remote_concurrency` and `--remote-concurrency`.

## Do not change

Source behavior; ledgers' existing rows; OpenAI.

## Dependencies already satisfied

- 01 and 02.

## Completion criteria

Combined validation passes with `RUN_LIVE_*` unset. `results.md` exists with measured numbers and the settlement or the reason a reservation is retained.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
