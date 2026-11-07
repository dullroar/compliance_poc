---
id: 04-runtime-wiring
status: pending
depends_on: [02-loan-officer-sheet, 03-examiner-finding]
touches:
  - compliance_common/narrative_schema.py
  - compliance_common/narrative.py
  - compliance_common/assemble.py
  - agents/runner.py
  - orchestrator/config.py
  - agents.yaml
  - builders/narrative_contract.md
  - prompts/*.md
  - tests/test_agent_runner.py
  - tests/test_response_runtime.py
lane: runtime
gate: python3 -m unittest tests.test_response_runtime tests.test_agent_runner tests.test_agent_parity -v
requirements: [R5, R7]
evidence: ""
---

# Put the templates into every domain result, with model phrasing and a code fallback

Write for an agent with no chat history.

## Change

- `NARRATIVE_SCHEMA`: add per-finding paragraphs keyed by rule id (strict). Keep a test that the schema matches `builders/narrative_contract.md`.
- `check_narrative`: apply grounding, contradiction, required-element and word-limit checks to each paragraph; violations drive the existing single retry, then code renders that paragraph.
- `assemble`: attach `response_templates: {loan_officer, examiner}` to each result, with each paragraph's source (`model`, `model_retry`, `code`).
- `agents.yaml` option `templates: model | code` (default `model`); read in `run_agent`. `code` makes no extra model request.
- Rebuild prompts with `python -m builders.build prompts` (version bump in the header line).
- Offline tests with fake clients: accepted, over-limit, ungrounded, malformed, `templates: code`, all eight domains and the auditor.

## Do not change

Rules, packs, evaluators, `decision_id`; the narrative role (step 05); live gates.

## Dependencies already satisfied

- 02 and 03: renderers and confirmed limits.

## Completion criteria

All registry roles return both templates on `sample_loan.json` with no change to `decision_id` or classification (parity suite unchanged and green).

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
