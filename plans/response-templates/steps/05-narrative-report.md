---
id: 05-narrative-report
status: pending
depends_on: [04-runtime-wiring]
touches:
  - prompts/narrative.md
  - builders/narrative_contract.md
  - compliance_common/templates/report.py
  - agents/runner.py
  - orchestrator/batch.py
  - orchestrator/cli.py
  - tests/test_report_assembly.py
lane: report
gate: python3 -m unittest tests.test_report_assembly tests.test_batch_concurrency -v
requirements: [R6, R7]
evidence: ""
---

# Assemble the report from the templates; the model writes only a short summary

Write for an agent with no chat history.

## Change

- `report.py`: code builds the report from domain results and the auditor result: loan-officer section, examiner section by regime, cross-regime findings.
- `prompts/narrative.md`: the model writes one summary of at most 150 words, grounded in the results; bump the version. Remove the multi-audience instructions.
- Keep `--narrative-out` behavior: a failed narrative stage still saves batch JSON and exits 1 with no empty report.
- Tests: assembly from fixtures, size bound, the failure behavior, and the narrative role output stays far below the output cap.

## Do not change

Domain agent behavior, orchestration order, concurrency.

## Dependencies already satisfied

- 04-runtime-wiring: `response_templates` on every result.

## Completion criteria

The report on `sample_loan.json` contains both templates for every regime and the auditor findings. The narrative model output is at most 150 words.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
