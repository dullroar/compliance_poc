---
id: 02-live-verification
status: pending
depends_on: [01-live-harness]
touches:
  - agents/backends.py
  - agents/runner.py
  - compliance_common/tools.py
  - tests/test_openai_live_smoke.py
  - tests/test_openai_smoke_accounting.py
  - plans/openai-smoketest/runs.jsonl
  - README.md
lane: serial
gate: RUN_LIVE_OPENAI_TESTS=1 python3 -m unittest discover -s tests -p test_openai_live_smoke.py -v
requirements: [R1, R2, R3]
evidence: ""
---

# Run the synthetic OpenAI smoke test and repair in-scope integration defects

## Change

- Run the gate with `gpt-6-luna` and the cumulative $20 spend bound. Verify credentials without printing them, inspect outbound material, and record per-mode and per-cycle requests, usage and costs in the persistent ledger. Each cycle has a six-request maximum; conservatively reserve budget before each request and preserve uncertain charges across cycles and restarts.
- If offline diagnosis identifies an existing provider integration defect, repair only the listed runtime paths within the existing provider contract and rerun offline checks; repeat a live cycle only after diagnosis and when its worst-case cost fits the remaining cumulative budget. Document the opt-in invocation and limitations in `README.md` without exposing credentials or payloads.

## Do not change

Evaluator behavior, defaults, fixture facts, or acceptance checks. Do not use non-synthetic input or exceed the approved request/spend limit.

## Dependencies already satisfied

Step 01 supplies the bounded test and offline opt-in checks.

## Completion criteria

Both seeded and model-directed A2A calls actually reach `gpt-6-luna`; all R1, R2 and R3 assertions pass. Record SDK/Python versions, command, elapsed time, request counts, API-reported tokens or explicit unknowns, pricing basis, estimated costs and reservations, parity, guard/fallback status, and result, without raw payloads or secrets. A skip, timeout, fallback, or request-cap breach fails the gate.

## Record

Retain failed cycles, their request counts, known usage and conservative reservations. Set `done` only with successful live evidence; otherwise block and escalate when the plan requires it.
