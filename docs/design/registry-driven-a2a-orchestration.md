---
gist: "Read when: adding or changing a domain agent, the registry (agents.yaml), A2A servers/Agent Cards, batch concurrency, or the auditor and narrative stages."
---

# Registry-driven A2A orchestration

- Agents are declarative registry entries rather than bespoke Python classes. Adding a domain agent should normally require prompt/spec work, not orchestration changes.
- Batch review runs domain agents concurrently over A2A, each independent of the others. This favors reproducible, attributable per-regime determinations over implicit cross-agent influence.
- The auditor is a distinct cross-regime stage; narrative generation is opt-in. A domain determination should not be silently rewritten into prose.
- A2A is the orchestration protocol. Each agent is a server with an Agent Card; local (Ollama) and remote (Anthropic) backends are a per-agent configuration in `agents.yaml`, not a protocol difference.
- Domain agents and the auditor share one tool-backed runtime (pinned canonical input, assembled result, verified narrative); the narrative agent is prompt-only and is not required to emit a decision. Tests enumerate the roles from the registry so a new entry is covered automatically.
- A failed agent is a result with `parse_error` and does not stop the batch; the auditor treats it as missing and the narrative agent is given the failure evidence, never an empty value.
- An A2A data part is a protobuf Struct, which turns integers into floats, and the evaluators' decision ids and record text depend on exact values. Clients therefore also send the payload as JSON text in `payload_json`, which the server prefers; a Struct-only request is still accepted but is not decision-identical.
