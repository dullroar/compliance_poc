---
id: 06-validate-and-close
status: pending
depends_on: [05-narrative-report]
touches:
  - tests/test_anthropic_live_parity.py
  - tests/test_anthropic_live_accounting.py
  - usage/anthropic-api-ledger.jsonl
  - plans/response-templates/results.md
  - plans/archive/live-parity/exception-record.md
  - README.md
  - memory/narrate-only-and-grounding-guards.md
lane: validate
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R6, R7]
evidence: ""
---

# Run the combined validation, retire the truncation tolerance and prove it live once

Write for an agent with no chat history.

## Change

- Remove `TOLERATED_TRUNCATION` and the test that pins it (R6 names this as the permitted exception to the protected-check rule). Mark exception 1 closed in the archived record with the date and the reason.
- Preflight: `anthropic_cost_estimator.py estimate` then `reserve`; recheck rates and date. Run `RUN_LIVE_ANTHROPIC_PARITY=1 python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v` once. The narrative role must pass `not_truncated` with no tolerance, and every role must still be `model` or `model_retry`.
- Write `plans/response-templates/results.md`: tokens and cost per role before (archived results) and after, word counts per regime, and any role that fell back to code paragraphs.
- README: operator notes for `templates`. Update the memory topic only if a non-obvious finding appears.

## Do not change

Rules, packs, other plans' files, existing ledger rows. No OpenAI live run.

## Dependencies already satisfied

- 05-narrative-report: the new report; all earlier steps.

## Completion criteria

Full offline suite, context and plan checks pass with `RUN_LIVE_*` unset. The live gate passes non-skipped with no tolerance. Reservation settled from API usage or retained with a reason.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
