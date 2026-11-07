---
id: 02-bar-and-sweep
status: pending
depends_on: [01-candidates-and-guard]
touches:
  - benchmarks/floor_bar.py
  - benchmarks/floor_sweep.py
  - tests/test_floor_bar.py
  - plans/tune-ais/scenarios.md
lane: sweep
gate: python3 -m unittest tests.test_floor_bar -v && python3 -m benchmarks.floor_sweep --dry-run
requirements: [R2, R3, R4, R6]
evidence: ""
---

# Encode the bar and the ladder, runnable offline with fakes

Write for an agent with no chat history.

## Change

- `floor_bar.py`: T1-T4 and the first-pass rule as pure functions over run records, with tests that must fail for each failure kind.
- `floor_sweep.py`: scenarios chosen by script and listed in `scenarios.md`; rungs 0-2; per-role climb and stop; a metadata-only run file; `--dry-run` with fake backends; a table matching the `floor.md` layout.
- **Stop and ask Jim to confirm the bar (R2), the scenarios, and the T5 sample size before step 03.**

## Do not change

Runtime code, prompts, ledgers.

## Dependencies already satisfied

- 01: candidates run and are priced.

## Completion criteria

Dry-run produces the full table. Bar tests pass. Jim's confirmation is recorded in the evidence.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
