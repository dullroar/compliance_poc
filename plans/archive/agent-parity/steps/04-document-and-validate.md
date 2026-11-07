---
id: 04-document-and-validate
status: done
depends_on: [03-orchestration]
touches:
  - README.md
  - docs/design/**
  - plans/agent-parity/inventory.md
  - plans/agent-parity/spec.md
  - plans/agent-parity/steps/04-document-and-validate.md
lane: serial
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R4]
evidence: "2026-11-06, Python 3.12.3. Corrected demonstrated stale documentation only: README (intro said seven agents; TRID missing from the Agents table; auditor/narrative notes; shared evaluator contract section with the YBS specifics kept; batch failure behavior; test description), docs/design/registry-driven-a2a-orchestration.md and raw-and-parsed-results-retained.md. Compliance-review caveats retained; no context index changes were needed (check passes). Inventory reviewed cell by cell against the registry (10 roles x 11 capabilities, plus 11 orchestration rows): every cell cites a proof, a repaired gap or a stated not-applicable reason; G1-G11, G14, G15 resolved, G12 documentation corrected, G13 not applicable (live services excluded by the spec); no item unknown or unresolved. Protected checks: git diff of tests shows one changed line (an import extended in test_batch_concurrency.py); no existing assertion, fixture, domain rule, pack, prompt, schema, agents.yaml or provider default was changed. Exact combined gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py -> exit 0; Ran 345 tests OK (3 skipped, opt-in live APOR/Ollama/OpenAI); build_context_indexes, check_plan, check_links, scan_context_secrets all ok."
---

# Align operator guidance and validate the integrated system

## Change

- Correct only demonstrated stale README and canonical design statements, including registry counts or YBS-pilot framing where inaccurate. Keep reviewer and compliance-approval caveats intact; regenerate context indexes if a routed file or gist changes.
- Review each inventory cell and gap against actual evidence; run the exact combined gate. Record the full results and update the spec status only after every requirement and protected check is satisfied.

## Do not change

Domain decisions, protected tests or unrelated documentation. Do not describe unknown or untested behavior as verified.

## Dependencies already satisfied

Steps 01-03 establish the baseline, domain contracts and role-specific orchestration evidence.

## Completion criteria

No inventory item remains unknown or unresolved; all registered roles are accounted for with evidence or justified not-applicable disposition. The full offline suite and context/plan checks pass. Record date, command, interpreter and test results.

## Record

Set `status: done` and the spec to `complete` only when all conditions pass; otherwise preserve evidence and follow escalation rules.
