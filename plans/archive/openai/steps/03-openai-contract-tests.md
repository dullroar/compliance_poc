---
id: 03-openai-contract-tests
status: done
depends_on: [01-provider-runtime]
touches:
  - tests/test_openai_backend.py
  - tests/test_ybs_evaluator.py
lane: provider-tests
gate: python3 -m unittest tests.test_openai_backend tests.test_ybs_evaluator -v
requirements: [R2, R4, R5]
evidence: >-
  2026-11-06: .venv/bin/python -m unittest tests.test_openai_backend tests.test_ybs_evaluator.YBSContractTests.test_openai_tool_loop_uses_the_same_deterministic_evaluator_offline tests.test_ybs_evaluator.ToolEnforcementFormatTests -v passed (12 tests), followed by python3 -m py_compile tests/test_openai_backend.py tests/test_ybs_evaluator.py. The named full gate was attempted with mcp 2.0.0 and 2.3.0 but did not complete: the unchanged YBSContractTests.test_all_provider_and_mcp_tools_share_one_contract_and_decision blocks while closing the in-process Client(ybs_server) after the evaluator returns. No production or protected-test behavior was changed to mask it.
  2026-11-06: With the archived MCP repair present, Python 3.12.3, mcp 2.0.0 and anyio 4.13.0, `timeout 30s python3 -m unittest tests.test_ybs_evaluator.YBSContractTests.test_all_provider_and_mcp_tools_share_one_contract_and_decision -v` timed out in the sandbox (exit 124); the same command passed outside the sandbox (1 test, 0.659s). The virtual environment was selected with `export PATH="$PWD/.venv/bin:$PATH"`.
  2026-11-06: Outside the sandbox with the same virtual environment and OpenAI SDK 3.46.0, `python3 -m unittest tests.test_openai_backend tests.test_ybs_evaluator -v` passed (19 tests, 1.662s). Added a separate OpenAI fake-client grounding test for an unsupported number and reran the exact gate: 20 tests, 1 failure, 1.710s. The guard rejected the number twice and selected deterministic fallback; the new test's assertion that the number is absent from all of `parsed` failed because `narrative_warnings` deliberately records the rejected number. The fallback's `compliance_determination_summary` did not contain it. A protected check failed; correction of the overbroad new assertion requires the owner's decision under the spec. Step 04 was not run.
  2026-11-06: Jim approved correcting the assertion to check the fallback narrative while retaining the diagnostic warning. The test now verifies both properties.
  2026-11-06: With `export PATH="$PWD/.venv/bin:$PATH"` selecting Python 3.12.3, mcp 2.0.0, anyio 4.13.0 and OpenAI SDK 3.46.0, `python3 -m unittest tests.test_openai_backend tests.test_ybs_evaluator -v` passed outside the sandbox (20 tests, 1.816s). The offline fake-client tests verify canonical argument pinning, seeded and model tool calls, and grounding retry followed by deterministic fallback; no API key or live OpenAI call is needed.
  2026-11-06: After the runtime fixes, added offline checks for explicit-model interactive chat and schema-constrained model tool calls. With the same virtual environment, `python3 -m unittest tests.test_openai_backend tests.test_ybs_evaluator -v` passed outside the sandbox (22 tests, 2.374s).
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
