---
id: 01-catalog
status: pending
depends_on: []
touches:
  - compliance_common/templates/catalog.py
  - compliance_common/templates/catalog/**
  - tests/test_response_catalog.py
lane: catalog
gate: python3 -m unittest tests.test_response_catalog -v
requirements: [R1, R2]
evidence: ""
---

# Build the template catalog and prove it covers every rule id and missing fact

Write for an agent with no chat history.

## Change

- `compliance_common/templates/catalog.py`: loader and resolver. Entries are keyed by exact rule id or by pattern (`HMDA-LAR-*`, `VMI-REQUEST-*`, `YBS-ENTITY-*`). Each entry holds: kind (G, V, R, P from [inventory.md](../inventory.md)), customer label, one-line reason (STE), regulation citation, examiner requirement text, action text, and who acts.
- `compliance_common/templates/catalog/<domain>.yaml`: one file per regime plus the auditor. Located outside every `pack/` so no `decision_id` changes.
- `tests/test_response_catalog.py` (write first): enumerate ids from the evaluators and fixtures and fail on any fall-through to the generic entry; assert editing an entry leaves `decision_id` unchanged; assert a made-up id resolves to the generic entry and is flagged.

## Do not change

Evaluators, packs, `decision.py`, existing tests.

## Dependencies already satisfied

- None. This is the first step.

## Completion criteria

All ids and missing-fact fields seen across `tests/fixtures/*/scenarios.json`, `sample_loan.json` and the HMDA LAR pack resolve to a specific entry. Regulation text in each entry is traceable to a pinned snapshot or `builders/sources.yaml` source.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
