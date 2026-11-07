---
id: 04-contract-and-suite
status: done
depends_on: [01-pin-mcp-runtime, 02-async-server-adapter, 03-stdio-transport]
touches:
  - tests/test_ybs_evaluator.py
  - tests/test_mcp_contract.py
  - README.md
lane: integration-validation
gate: .venv/bin/python -m unittest discover -s tests -v && .venv/bin/python scripts/check_context.py && .venv/bin/python scripts/check_plan.py
requirements: [R1, R2, R3, R4]
evidence: >-
  2026-11-06: Python 3.12.3, mcp 2.0.0, anyio 4.13.0. Outside the sandbox,
  `timeout 20s .venv/bin/python -m unittest tests.test_mcp_contract tests.test_ybs_evaluator.YBSContractTests.test_all_provider_and_mcp_tools_share_one_contract_and_decision -v`
  passed (3 tests, 1.292s); direct, in-process and stdio results matched in decision
  ID and classification. The exact combined gate
  `.venv/bin/python -m unittest discover -s tests -v && .venv/bin/python scripts/check_context.py && .venv/bin/python scripts/check_plan.py`
  passed outside the sandbox: 275 tests in 29.053s, with 2 existing opt-in live tests
  skipped, and both validation scripts passed. The suite includes the inherited OpenAI
  provider tests; the separate OpenAI plan remains blocked and was not completed.
---

# Restore transport-separated contract coverage and run the offline suite

Repair the existing YBS contract coverage so it reports accurate failure locations, retains direct/in-process/stdio parity checks, and validates the integrated repair without weakening its authority assertions.

## Change

- `tests/test_ybs_evaluator.py`: update the existing shared contract test only as needed to use the repaired helpers and to make in-process versus stdio assertions explicit.
- `tests/test_mcp_contract.py`: add integration-focused assertions that distinguish direct evaluator, in-process client, and stdio subprocess lifecycle behavior without duplicating evaluator fixtures.
- `README.md`: update the MCP invocation/testing instructions only if the selected dependency and transport API materially changes an operator-facing command.

## Do not change

- Existing evaluator fixtures, canonical-case semantics, deterministic decision assertions, protected narrative safeguards, or the full-suite command. Do not label a timeout as an unavailable test.

## Dependencies already satisfied

- `01-pin-mcp-runtime` supplies the reproducible SDK environment.
- `02-async-server-adapter` supplies safe in-process execution for synchronous evaluators.
- `03-stdio-transport` supplies the SDK-correct subprocess transport.

## Completion criteria

- The prior hanging shared YBS contract test completes within a bounded test run and identifies whether a failure is in-process or stdio.
- Direct, in-process, and subprocess paths produce the same deterministic YBS decision for the same canonical case.
- The complete offline suite, context validation, and plan validation pass without modifying protected tests to conceal a failure.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
