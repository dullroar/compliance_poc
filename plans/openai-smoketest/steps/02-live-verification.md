---
id: 02-live-verification
status: pending
depends_on: [01-live-harness]
touches:
  - agents/backends.py
  - agents/runner.py
  - compliance_common/tools.py
  - tests/test_openai_live_smoke.py
  - README.md
lane: serial
gate: RUN_LIVE_OPENAI_TESTS=1 python3 -m unittest discover -s tests -p test_openai_live_smoke.py -v
requirements: [R1, R2]
evidence: ""
---

# Run the synthetic OpenAI smoke test and repair in-scope integration defects

## Change

- Run the gate once with the approved model IDs and spend bound. Verify credentials are available without printing them, inspect outbound material, and record actual per-model and total request counts across both modes. A maximum of six Responses requests per model and six times the number of selected models overall applies to the entire attempt.
- If offline diagnosis identifies an existing provider integration defect, repair only the listed runtime paths within the existing provider contract and rerun offline checks; do not silently repeat an exhausted live attempt. Document the opt-in invocation and limitations in `README.md` without exposing credentials or payloads.

## Do not change

Evaluator behavior, defaults, fixture facts, or acceptance checks. Do not use non-synthetic input or exceed the approved request/spend limit.

## Dependencies already satisfied

Step 01 supplies the bounded test and offline opt-in checks.

## Completion criteria

Both seeded and model-directed A2A calls actually reach every approved OpenAI model; all R1 and R2 assertions pass. Record model IDs, SDK/Python versions, command, elapsed time, per-model and total request counts, parity, guard/fallback status, and result, without raw payloads or secrets. A skip, timeout, fallback, or request-cap breach fails the gate.

## Record

Retain failed attempts and their request counts. Set `done` only with successful live evidence; otherwise block and escalate when the plan requires it.
