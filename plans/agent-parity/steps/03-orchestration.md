---
id: 03-orchestration
status: pending
depends_on: [02-domain-contracts]
touches:
  - agents/a2a_server.py
  - orchestrator/**
  - agents.yaml
  - tests/**
  - plans/agent-parity/inventory.md
lane: serial
gate: python3 -m unittest discover -s tests -p test_a2a.py -v && python3 -m unittest discover -s tests -p test_batch_concurrency.py -v && python3 -m unittest discover -s tests -p test_agent_parity.py -v
requirements: [R3]
evidence: ""
---

# Verify A2A role coverage and batch behavior

## Change

- Extend offline A2A/batch tests to cover all configured cards and role-appropriate tasks, selection, bounded concurrency, auditor-after-domains, optional narrative-after-auditor, failure isolation, and raw/parsed/failure evidence. Use fake backends and synthetic data.
- Fix demonstrated integration gaps in the listed server, orchestration and registry paths. Update inventory with references, tests and justified role exceptions.

## Do not change

Regulatory rules, evaluator schemas or outcomes, protected tests, default provider/model, or external systems.

## Dependencies already satisfied

Steps 01 and 02 provide the inventory and per-domain runtime contracts.

## Completion criteria

The exact gate passes, all registered roles and their applicable R3 behavior are tested, and demonstrated gaps have evidence-backed dispositions. Any requirement for a business-rule change is escalated.

## Record

Record date, command, covered roles and results in `evidence:` before marking done.
