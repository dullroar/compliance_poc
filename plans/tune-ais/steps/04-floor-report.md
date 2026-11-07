---
id: 04-floor-report
status: pending
depends_on: [03-live-sweep]
touches:
  - plans/tune-ais/floor.md
  - memory/model-floor.md
  - README.md
lane: report
gate: python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R2, R4, R6]
evidence: ""
---

# Write the dated floor, get the T5 reads, and propose config changes

Write for an agent with no chat history.

## Change

- Select the T5 paragraph sample by script from the cheapest passing rung and give it to Jim for the 12 reads; record each answer.
- Write `floor.md` (per role: lowest passing rung, cost per successful narrative, tokens, latency, date, pricing source, ledger rows, what was not tested). Add `memory/model-floor.md` (gist line, one paragraph, the re-run command, the date after which to distrust it). README note on the command.
- Propose `agents.yaml` changes (per-role model, `templates: code` where rung 0 passes). **Do not apply them. Ask Jim.**

## Do not change

`agents.yaml`, provider defaults, source.

## Dependencies already satisfied

- 03: the evidence.

## Completion criteria

Floor report and memory topic exist; context and plan checks pass. Jim has the proposal and the T5 result.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
