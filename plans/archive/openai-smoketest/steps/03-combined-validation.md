---
id: 03-combined-validation
status: done
depends_on: [02-live-verification]
touches:
  - plans/openai-smoketest/spec.md
  - plans/openai-smoketest/steps/03-combined-validation.md
lane: serial
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R4]
evidence: "2026-11-06: With Python 3.12.3 from .venv/bin on PATH and RUN_LIVE_OPENAI_TESTS unset, ran the exact combined gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py. The suite passed 289 tests in 26.420 seconds with 3 opt-in live tests skipped, including the OpenAI test; all context, index, link, secret-scan and plan checks passed. The separately run, non-skipped live gate passed both modes; step 02 and runs.jsonl record the cycle, request usage, conservative spending and guarded narrative outcomes. Tests ran outside the execution sandbox because its Python thread cleanup stalls."
---

# Verify the integrated result and record completion

## Change

- Run the exact gate with `RUN_LIVE_OPENAI_TESTS` unset. Review all step evidence, including the separately completed non-skipped live gate and its usage ledger. Update this step and the spec status only after all checks and requirements pass.

## Do not change

Protected checks, live-test evidence, evaluator behavior, or unrelated work.

## Dependencies already satisfied

Steps 01 and 02 supply the harness and successful real-provider evidence.

## Completion criteria

The full offline suite and context/plan checks pass; the live test skips offline; every requirement and protected check has evidence. Record date, commands, Python version, test counts and results.

## Record

Set `status: done` and the spec to `complete` only when all conditions pass; otherwise preserve evidence and follow the escalation rules.
