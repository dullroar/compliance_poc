# DESIGN.md

# Compliance Agent Orchestrator Design

## Boundary

The repository separates regulatory expertise from orchestration. The versioned agent-specification documents and the prompt registry carry domain rules; `compliance_orchestrator.py` supplies provider access, execution modes, and result handling. README.md is the operator guide.

## Core decisions

- Agents are declarative registry entries rather than bespoke Python classes. Adding a domain agent should normally require prompt/spec work, not orchestration changes.
- Batch review runs domain agents sequentially and independently. This favors reproducible, attributable per-regime determinations over implicit cross-agent influence.
- The auditor is a distinct cross-regime stage; narrative generation is opt-in. A domain determination should not be silently rewritten into prose.
- Provider handling is intentionally small: Anthropic and Ollama expose the same internal message path, while Ollama uses its native HTTP API to avoid a second provider dependency. The local Ollama default is `gemma4:26b`; `COMPLIANCE_MODEL` and the CLI `--model` option remain explicit overrides for reproducible alternative-model runs.
- Results retain both raw model text and parsed JSON. Parse failures remain observable evidence instead of being discarded or silently repaired.

## Constraints

This is a decision-support prototype, not an automated compliance authority or filing system. Missing evidence must remain visible in the structured result rather than being invented by the orchestrator.


