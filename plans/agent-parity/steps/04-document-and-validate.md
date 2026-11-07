---
id: 04-document-and-validate
status: pending
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
evidence: ""
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
