# Operational memory

Non-obvious findings that would cost time to rediscover: environment quirks, failure causes, tool
limitations, verified platform behavior. Open only the topic whose **Read when** line matches the task.

How to add a finding: put it in the existing topic file if one fits, otherwise create one topic per file
with `gist: "Read when: ..."` front matter. State the date, the observation, and the conditions; note when
it may be obsolete. Correct a changed finding in place rather than appending a rival entry. No secrets,
personal data, personal paths or raw logs.

<!-- BEGIN GENERATED CONTEXT INDEX -->

* [anthropic-max-tokens-truncation.md](./anthropic-max-tokens-truncation.md).
  Read when: Anthropic domain-agent calls produce JSON parse errors, or an agent's output schema gains fields.
* [local-model-sizing-and-selection.md](./local-model-sizing-and-selection.md).
  Read when: choosing or comparing local models, judging pipeline latency, or interpreting model benchmark results.
* [model-floor.md](./model-floor.md).
  Read when: deciding which Claude model or setting a role needs, or before changing agents.yaml models or templates, or when the model floor report may be out of date.
* [narrate-only-and-grounding-guards.md](./narrate-only-and-grounding-guards.md).
  Read when: a narrative contradicts the decision record, evidence appears fabricated, or the grounding and fact-check guards are changed.
* [ollama-service-and-context-limits.md](./ollama-service-and-context-limits.md).
  Read when: Ollama output is truncated or plausible-but-wrong, a long run is interrupted, the Ollama service settings need changing, or fit and speed of a loaded model are in question.
* [reg-b-marital-status-correction.md](./reg-b-marital-status-correction.md).
  Read when: an agent flags missing marital status or other demographic data under HMDA or ECOA.
* [regulation-source-access.md](./regulation-source-access.md).
  Read when: fetching or rebuilding from eCFR, FFIEC, FEMA or FCA sources, or a source returns 403/404/406.
* [sdk-migration-quirks.md](./sdk-migration-quirks.md).
  Read when: upgrading or testing against the mcp 2.x or a2a-sdk 1.x libraries, or an A2A task fails with an enqueue-order error.
* [thinking-tokens-and-benchmark-gotchas.md](./thinking-tokens-and-benchmark-gotchas.md).
  Read when: benchmarking models, a model's latency is unexpectedly high, or JSON parsing sees inline think tags.
* [tool-calling-and-harness-fallback.md](./tool-calling-and-harness-fallback.md).
  Read when: a model skips or malforms its MCP tool call, a tool_calls entry shows by=harness, or choosing tool_mode for a small model.

<!-- END GENERATED CONTEXT INDEX -->
