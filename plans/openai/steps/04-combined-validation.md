---
id: 04-combined-validation
status: pending
depends_on: [01-provider-runtime, 02-operator-configuration, 03-openai-contract-tests]
touches:
  - plans/openai/steps/04-combined-validation.md
lane: validation
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R3, R5]
evidence: ""
---

# Verify the integrated change and record reproducible evidence

Run the complete offline validation suite after the independent provider and documentation work has merged, then record exact outcomes here.

## Change

- `plans/openai/steps/04-combined-validation.md`: mark the step done and record the date, commands, results, and any intentionally unavailable live verification.

## Do not change

- Source behavior merely to make a test pass; protected checks, requirements, evaluator contracts, and scope remain unchanged.
- Do not substitute a live API call for offline validation or send non-synthetic data.

## Dependencies already satisfied

- `01-provider-runtime` provides the adapter.
- `02-operator-configuration` provides bounded operator documentation.
- `03-openai-contract-tests` provides offline provider evidence.

## Completion criteria

- The combined gate passes with the new provider tests included.
- Any absent live smoke test is explicitly recorded as unavailable because it requires separate owner authority; it is not treated as a failure or silently omitted.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
