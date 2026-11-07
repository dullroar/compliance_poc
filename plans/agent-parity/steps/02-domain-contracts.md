---
id: 02-domain-contracts
status: pending
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
evidence: ""
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
