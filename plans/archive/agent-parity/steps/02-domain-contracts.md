---
id: 02-domain-contracts
status: done
depends_on: [01-inventory]
touches:
  - agents/runner.py
  - agents/a2a_server.py
  - compliance_common/**
  - compliance_mcp/**/adapter.py
  - compliance_mcp/**/server.py
  - tests/**
  - plans/agent-parity/inventory.md
lane: serial
gate: python3 -m unittest discover -s tests -p test_agent_parity.py -v && python3 -m unittest discover -s tests -p test_mcp_contract.py -v
requirements: [R2]
evidence: "2026-11-06, Python 3.12.3. Added tests/test_agent_parity.py (19 tests) enumerating roles from agents.yaml: hmda, ecoa, hvcre, hpml, trid, fzd, ybs, vmi plus the auditor as its own role (narrative has no tool; covered in step 03). Initial run failed: (a) every non-trivial A2A task returned a different decision_id for hmda/hpml/trid/vmi/ybs/auditor because protobuf Struct turns integers into floats (G15); (b) evaluator rejections surfaced as an opaque ExceptionGroup (G14). Repairs: compliance_common/mcp_client.py unwraps task-group errors; agents/a2a_server.py accepts exact JSON in payload_json (legacy payload still accepted). The production client orchestrator/a2a_client.py is outside this step's touches, so its half of G15 is carried to step 03; until then the test sends payload_json through a test-side part builder. Gate: python3 -m unittest discover -s tests -p test_agent_parity.py -v -> 19 OK; python3 -m unittest discover -s tests -p test_mcp_contract.py -v -> 2 OK. Full suite python3 -m unittest discover -s tests -> 325 tests OK, 3 skipped (opt-in live); no existing test or fixture modified. Inventory dispositions: G1-G5, G7 resolved; G6 partly; G14 resolved; G15 server half resolved."
---

# Close verified domain runtime and transport gaps

## Change

- Add `tests/test_agent_parity.py` using synthetic inputs and fake narrators to enumerate evaluator-backed domains from the registry. Cover direct/MCP stdio/A2A decision parity, bounded process cleanup, canonical argument pinning, missing case behavior, both tool modes, guard/fallback and retained metadata, using domain-appropriate assertions.
- Repair only demonstrated shared runtime, adapter or server integration gaps in the listed paths. Add synthetic fixtures if needed; do not modify existing evaluator expectations. Record evidence and resolved/not-applicable dispositions in the inventory.

## Do not change

Regulatory rules, packs, prompts, schemas, classifications, provider defaults or protected checks.

## Dependencies already satisfied

Step 01 identifies the actual role set, baseline and gaps.

## Completion criteria

The gate passes and coverage names every configured evaluator-backed domain; direct, stdio and A2A results match each domain's own authority fields. New failures have evidence and are repaired or escalated; no unverified item is marked complete.

## Record

Record date, commands, covered roles, results and inventory dispositions in `evidence:` before marking done.
