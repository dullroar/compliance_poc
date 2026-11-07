---
id: 02-guard-thread-safety
status: pending
depends_on: []
touches:
  - tests/live_parity_common.py
  - tests/test_anthropic_live_parity.py
  - tests/test_openai_live_parity.py
  - tests/test_anthropic_live_accounting.py
  - tests/test_openai_live_parity_accounting.py
lane: guards
gate: python3 -m unittest tests.test_anthropic_live_accounting tests.test_openai_live_parity_accounting tests.test_live_parity_common -v
requirements: [R4, R6]
evidence: ""
---

# Make the live request guards safe under simultaneous calls

Write for an agent with no chat history.

## Change

- Find every shared counter and every file or ledger write in the guarded clients and the shared live helper; put them under one lock.
- Add concurrent stress tests with a fake transport (cap exactness, refusal of extras, exact ledger totals, restart replay).
- Do not change cap values, models, reservations or any existing assertion. Live gates keep `concurrency=1`.

## Do not change

Existing assertions, request caps, the ledgers' rows, the estimators.

## Dependencies already satisfied

- None. Independent of 01 (no shared `touches`).

## Completion criteria

Stress tests pass repeatedly (run them at least 20 times and record the count). Existing tests pass unmodified.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
