---
gist: "Read when: adding or changing a domain agent, the registry (agents.yaml), A2A servers/Agent Cards, batch concurrency, or the auditor and narrative stages."
---

# Registry-driven A2A orchestration

- Agents are declarative registry entries rather than bespoke Python classes. Adding a domain agent should normally require prompt/spec work, not orchestration changes.
- Batch review runs domain agents concurrently over A2A, each independent of the others. This favors reproducible, attributable per-regime determinations over implicit cross-agent influence.
- The auditor is a distinct cross-regime stage; narrative generation is opt-in. A domain determination should not be silently rewritten into prose.
- A2A is the orchestration protocol. Each agent is a server with an Agent Card; local (Ollama) and remote (Anthropic) backends are a per-agent configuration in `agents.yaml`, not a protocol difference.
