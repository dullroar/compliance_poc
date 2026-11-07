---
id: 03-orchestration
status: done
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
evidence: "2026-11-06, Python 3.12.3. Registry (agents.yaml, 10): hmda, ecoa, hvcre, hpml, trid, fzd, ybs, vmi, auditor, narrative. Added tests: tests/test_a2a.py::EveryRegisteredRoleTests (cards for all 10 roles, result+decision artifacts for hpml and auditor, result+report with no decision for narrative, prose answer retains raw text/parse error, registry options reach the executor); tests/test_batch_concurrency.py WholeRegistryBatchTests, BatchCommandTests, RegistryOptionsTests (default selection from registry, concurrency bound 1 and 3, selection order, unknown keys, failure isolation, real auditor adapter marks failed domains missing, failed auditor/narrative visible, narrative after auditor, CLI exit behavior); tests/test_agent_parity.py PayloadFidelityTests now use the production client. Existing tests in these files unchanged (new classes appended). Reproduced before repair with a failing fake narrator: G9 empty report reported as written; G10 narrative input {'hmda': ''}. Repairs: orchestrator/cli.py (failed narrative: stderr reason, no report, exit 1, batch JSON already saved); orchestrator/batch.py (failed agent passed on as {agent_key, status: failed, failure}); orchestrator/a2a_client.py (sends payload_json beside payload, completing G15). Gate: python3 -m unittest discover -s tests -p test_a2a.py -v -> 8 OK; -p test_batch_concurrency.py -v -> 16 OK; -p test_agent_parity.py -v -> 20 OK. Full suite python3 -m unittest discover -s tests -> 345 tests OK, 3 skipped (opt-in live). Inventory: G6, G8-G11, G15 resolved; only G12 (docs) open."
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
