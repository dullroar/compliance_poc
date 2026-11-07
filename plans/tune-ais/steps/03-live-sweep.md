---
id: 03-live-sweep
status: pending
depends_on: [02-bar-and-sweep]
touches:
  - usage/anthropic-api-ledger.jsonl
  - plans/tune-ais/runs-anthropic.jsonl
lane: live
gate: python3 -m benchmarks.floor_sweep --live --provider anthropic
requirements: [R1, R2, R3, R5]
evidence: ""
---

# Run the bounded live sweep, cheapest rung first

Write for an agent with no chat history.

## Change

- Per-new-model one-request diagnostic (forced tool choice behavior on Haiku 5.5; Sonnet 5.5 model mode).
- Run rung 1 for all roles, three repetitions of each scenario in both tool modes; run rung 2 only for roles that failed rung 1. Rung 0 needs no live call but is scored by the same bar.
- Reserve before each run; settle from usage; stop before R5's bound. Record usage per request. A skip, timeout or fallback is not a pass.

## Do not change

Source, prompts, the bar, existing ledger rows.

## Dependencies already satisfied

- 02: harness and confirmed bar.

## Completion criteria

Every role has a pass or fail for every rung tried. The ledger shows reservations, settlements and a total at or under USD 5.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
