# DESIGN.md

# Compliance Agent Orchestrator Design

## Boundary

The repository separates regulatory expertise from orchestration. The long-form specs (`specs/`) and the runtime prompts (`prompts/`, version in the header line) carry domain rules; `orchestrator/` (A2A client, batch, CLI) and `agents/` (A2A servers, backends, runner) supply provider access, execution modes, and result handling. README.md is the operator guide.

## Core decisions

- Agents are declarative registry entries rather than bespoke Python classes. Adding a domain agent should normally require prompt/spec work, not orchestration changes.
- Batch review runs domain agents concurrently over A2A, each independent of the others. This favors reproducible, attributable per-regime determinations over implicit cross-agent influence.
- The auditor is a distinct cross-regime stage; narrative generation is opt-in. A domain determination should not be silently rewritten into prose.
- Provider handling is intentionally small: Anthropic and Ollama expose the same internal message path, while Ollama uses its native HTTP API to avoid a second provider dependency. The local Ollama default is `gemma4:26b`; `COMPLIANCE_MODEL` and the CLI `--model` option remain explicit overrides for reproducible alternative-model runs.
- Results retain both raw model text and parsed JSON. Parse failures remain observable evidence instead of being discarded or silently repaired.

## Constraints

This is a decision-support prototype, not an automated compliance authority or filing system. Missing evidence must remain visible in the structured result rather than being invented by the orchestrator.


- Code decides, agents narrate. Each domain has a deterministic evaluator exposed as an MCP tool (`compliance_mcp/<domain>/`). The agent calls the tool, the harness pins the tool arguments to the loan payload, and `compliance_common/assemble.py` builds the result from the tool's decision record plus the model's prose; decision-owned fields the model emits are stripped and logged.
- Versions live inside the artifacts (prompt header line, `EVALUATOR_VERSION`, pack manifest), never in file or directory names; git carries history. Each component is versioned independently.
- A2A is the orchestration protocol. Each agent is a server with an Agent Card; local (Ollama) and remote (Anthropic) backends are a per-agent configuration in `agents.yaml`, not a protocol difference.
- Builders are agents with a deterministic harness: the registry of canonical sources and a lock file decide what is rebuilt; the harness owns snapshots, manifest provenance, path guards, version bumps, test runs and rollback. Builder output is always a reviewable proposal.
- Absence is never compliance. When a fact needed for a rule is not supplied, the rule's outcome is `unable_to_determine` and the fact is listed in `missing_facts`; the evaluators do not treat silence as "not applicable". Judgment calls that the regulation leaves to the institution (for example whether a loan is primarily agricultural) are input facts with an explicit `undetermined` value that yields a Review Required result.
