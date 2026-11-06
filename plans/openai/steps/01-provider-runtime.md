---
id: 01-provider-runtime
status: done
depends_on: []
touches:
  - agents/backends.py
  - compliance_common/tools.py
  - requirements.txt
  - orchestrator/cli.py
lane: provider-runtime
gate: python3 -m py_compile agents/backends.py compliance_common/tools.py orchestrator/cli.py
requirements: [R1, R2, R4]
evidence: "2026-11-06: python3 -m py_compile agents/backends.py compliance_common/tools.py orchestrator/cli.py passed; dependency-free fake Responses-client smoke passed. Existing tests.test_ybs_evaluator and tests.test_agent_runner were unavailable because mcp is not installed in this checkout."
---

# Add the OpenAI runtime provider behind the existing backend interface

Implement an `openai` provider using the official Python SDK and the Responses API, without changing evaluator logic or the default provider.

## Change

- `agents/backends.py`: add OpenAI client construction from `OPENAI_API_KEY`; explicit model, timeout, retry, and state-storage settings; response-text extraction; structured output for narrative schemas; and both the seeded and model-driven single-function paths.
- `compliance_common/tools.py`: add the OpenAI-native declaration and seeded function-call/function-call-output representation while preserving the shared MCP tool-spec contract.
- `requirements.txt`: add the official OpenAI Python dependency with a compatible minimum version.
- `orchestrator/cli.py`: accept `openai` wherever the runtime provider choices are validated; do not add it to builder CLI choices.

## Do not change

- `compliance_mcp/**`, `specs/**`, `prompts/**`, deterministic narrative assembly/guards, default provider/model selection, builder provider choices, or A2A protocol behavior.
- Do not issue a real network request or add a secret.

## Dependencies already satisfied

- None.

## Completion criteria

- All three backend methods retain their caller-visible contracts for `openai`.
- The OpenAI path uses only custom evaluator function declarations when a function is needed; it disables parallel calls and does not enable web search, file search, or hosted-agent facilities.
- Canonical evaluator arguments continue to be pinned by `agents.runner`; structured narrative output is requested with the existing `NARRATIVE_SCHEMA`.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
