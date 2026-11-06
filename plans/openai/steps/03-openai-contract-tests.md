---
id: 03-openai-contract-tests
status: pending
depends_on: [01-provider-runtime]
touches:
  - tests/test_openai_backend.py
  - tests/test_ybs_evaluator.py
lane: provider-tests
gate: python3 -m unittest tests.test_openai_backend tests.test_ybs_evaluator -v
requirements: [R2, R4, R5]
evidence: ""
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
