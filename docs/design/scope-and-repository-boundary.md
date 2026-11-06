---
gist: "Read when: deciding whether a change belongs in specs/prompts versus orchestrator/agents, or whether the tool may make compliance determinations on its own."
---

# Scope and repository boundary

The repository separates regulatory expertise from orchestration. The long-form specs (`specs/`) and the runtime prompts (`prompts/`, version in the header line) carry domain rules; `orchestrator/` (A2A client, batch, CLI) and `agents/` (A2A servers, backends, runner) supply provider access, execution modes, and result handling. README.md is the operator guide.

**Constraint.** This is a decision-support prototype, not an automated compliance authority or filing system. Missing evidence must remain visible in the structured result rather than being invented by the orchestrator.
