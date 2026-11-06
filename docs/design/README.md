---
gist: "Read when: changing the repository's design, boundaries or dependencies, or before simplifying a deliberate seam."
---

# Architecture premises

One durable design decision per file: the constraint, the choice, why, and what would contradict it. Open only the premise whose **Read when** line matches the task.

<!-- BEGIN GENERATED CONTEXT INDEX -->

* [absence-is-never-compliance.md](./absence-is-never-compliance.md).
  Read when: writing or changing a rule evaluator, the handling of missing facts, undetermined judgment calls, or Review Required outcomes.
* [builders-propose-reviewable-output.md](./builders-propose-reviewable-output.md).
  Read when: changing builder agents, the source registry and lock file, snapshots, path guards, version bumps or rollback.
* [code-decides-agents-narrate.md](./code-decides-agents-narrate.md).
  Read when: changing what a model may write in a result, the decision record assembly, narrative checks, or an evaluator MCP tool.
* [provider-and-model-selection.md](./provider-and-model-selection.md).
  Read when: adding a provider, changing the default model or COMPLIANCE_MODEL, or assigning models by role.
* [raw-and-parsed-results-retained.md](./raw-and-parsed-results-retained.md).
  Read when: changing result structure, parse-failure handling, or any logic that repairs or discards model output.
* [registry-driven-a2a-orchestration.md](./registry-driven-a2a-orchestration.md).
  Read when: adding or changing a domain agent, the registry (agents.yaml), A2A servers/Agent Cards, batch concurrency, or the auditor and narrative stages.
* [scope-and-repository-boundary.md](./scope-and-repository-boundary.md).
  Read when: deciding whether a change belongs in specs/prompts versus orchestrator/agents, or whether the tool may make compliance determinations on its own.
* [versions-live-in-artifacts.md](./versions-live-in-artifacts.md).
  Read when: bumping or naming a prompt, evaluator, or pack version, or tempted to put a version in a file or directory name.

<!-- END GENERATED CONTEXT INDEX -->
