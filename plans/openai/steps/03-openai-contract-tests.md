---
id: 03-openai-contract-tests
status: blocked
depends_on: [01-provider-runtime]
touches:
  - tests/test_openai_backend.py
  - tests/test_ybs_evaluator.py
lane: provider-tests
gate: python3 -m unittest tests.test_openai_backend tests.test_ybs_evaluator -v
requirements: [R2, R4, R5]
evidence: "2026-11-06: .venv/bin/python -m unittest tests.test_openai_backend tests.test_ybs_evaluator.YBSContractTests.test_openai_tool_loop_uses_the_same_deterministic_evaluator_offline tests.test_ybs_evaluator.ToolEnforcementFormatTests -v passed (12 tests), followed by python3 -m py_compile tests/test_openai_backend.py tests/test_ybs_evaluator.py. The named full gate was attempted with mcp 2.0.0 and 2.3.0 but did not complete: the unchanged YBSContractTests.test_all_provider_and_mcp_tools_share_one_contract_and_decision blocks while closing the in-process Client(ybs_server) after the evaluator returns. No production or protected-test behavior was changed to mask it."
---

# Prove the OpenAI adapter cannot weaken evaluator or narrative safeguards

Use offline fake Responses-client fixtures to validate the request/response protocol and error behavior.

## Change

- `tests/test_openai_backend.py`: test key validation, model selection, ordinary completion, schema-constrained narration, seeded tool-result continuation, model-mode forced single evaluator call, refusal/malformed output, timeout/rate-limit/error propagation, and no-network operation.
- `tests/test_ybs_evaluator.py`: extend the shared provider/MCP contract assertions only where needed to show that OpenAI receives the same evaluator specification and preserves the deterministic decision.

## Do not change

- Production credentials, network settings, evaluator implementations, protected test assertions, or actual OpenAI account state.

## Dependencies already satisfied

- `01-provider-runtime` supplies the provider and native tool translation under test.

## Completion criteria

- Tests verify that model-proposed evaluator arguments cannot alter canonical facts or the final decision.
- Tests verify the existing grounding retry/fallback behavior still applies to OpenAI-produced narrative text.
- Every test runs with a fake client and no API key.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
