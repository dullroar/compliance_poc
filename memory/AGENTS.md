# Memory index

<!-- IMMUTABLE HEADER: do not edit the text above the BEGIN marker. -->

This folder holds memories for agents. Humans read `docs/` instead.

- One memory is one file. Many agents can write at the same time without a lock.
- Each file starts with a `gist` in front matter. Use `Read me when:` for new files. Existing `Read when:` lines also work.
- Edit the existing file for a topic. Do not add a second file for the same topic.
- **NEVER put PII, secrets, keys, tokens, passwords, personal paths or private host names in a memory.** Memory files are tracked by Git and can become public.
- Write in Simplified Technical English (ASD-STE100).
- This file is generated. Run `python3 scripts/build_indexes.py` after any change. Do not edit the list below by hand.

Open only the files whose routing lines match your task.

<!-- BEGIN GENERATED INDEX -->

* [anthropic-max-tokens-truncation.md](./anthropic-max-tokens-truncation.md)
  Read when: Anthropic domain-agent calls produce JSON parse errors, or an agent's output schema gains fields.
* [local-model-sizing-and-selection.md](./local-model-sizing-and-selection.md)
  Read when: choosing or comparing local models, judging pipeline latency, or interpreting model benchmark results.
* [model-floor.md](./model-floor.md)
  Read when: deciding which Claude model or setting a role needs, or before changing agents.yaml models or templates, or when the model floor report may be out of date.
* [narrate-only-and-grounding-guards.md](./narrate-only-and-grounding-guards.md)
  Read when: a narrative contradicts the decision record, evidence appears fabricated, or the grounding and fact-check guards are changed.
* [ollama-service-and-context-limits.md](./ollama-service-and-context-limits.md)
  Read when: Ollama output is truncated or plausible-but-wrong, a long run is interrupted, the Ollama service settings need changing, or fit and speed of a loaded model are in question.
* [reg-b-marital-status-correction.md](./reg-b-marital-status-correction.md)
  Read when: an agent flags missing marital status or other demographic data under HMDA or ECOA.
* [regulation-source-access.md](./regulation-source-access.md)
  Read when: fetching or rebuilding from eCFR, FFIEC, FEMA or FCA sources, or a source returns 403/404/406.
* [sdk-migration-quirks.md](./sdk-migration-quirks.md)
  Read when: upgrading or testing against the mcp 2.x or a2a-sdk 1.x libraries, or an A2A task fails with an enqueue-order error.
* [thinking-tokens-and-benchmark-gotchas.md](./thinking-tokens-and-benchmark-gotchas.md)
  Read when: benchmarking models, a model's latency is unexpectedly high, or JSON parsing sees inline think tags.
* [tool-calling-and-harness-fallback.md](./tool-calling-and-harness-fallback.md)
  Read when: a model skips or malforms its MCP tool call, a tool_calls entry shows by=harness, or choosing tool_mode for a small model.

<!-- END GENERATED INDEX -->
