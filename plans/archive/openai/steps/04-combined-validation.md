---
id: 04-combined-validation
status: done
depends_on: [01-provider-runtime, 02-operator-configuration, 03-openai-contract-tests]
touches:
  - plans/archive/openai/steps/04-combined-validation.md
lane: validation
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R3, R5]
evidence: >-
  2026-11-06: With the virtual environment selected and Python 3.12.3, `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py` passed outside the sandbox (276 tests in 26.900s, 2 opt-in live tests skipped; both scripts passed). Subsequent requirement review identified runtime gaps in interactive explicit-model selection and model-driven structured narration, so this result predates the fixes and the combined gate must be rerun.
  2026-11-06: After those fixes, with `export PATH="$PWD/.venv/bin:$PATH"` selecting Python 3.12.3, mcp 2.0.0, anyio 4.13.0 and OpenAI SDK 3.46.0, the exact combined gate `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py` passed outside the sandbox: 278 tests in 30.143s, 2 existing opt-in live tests skipped; context and plan validation passed. No live OpenAI smoke test was performed because it requires separate owner authority; offline validation does not verify a particular account or model's live behavior.
---

# Verify the integrated change and record reproducible evidence

Run the complete offline validation suite after the independent provider and documentation work has merged, then record exact outcomes here.

## Change

- `plans/archive/openai/steps/04-combined-validation.md`: mark the step done and record the date, commands, results, and any intentionally unavailable live verification.

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
