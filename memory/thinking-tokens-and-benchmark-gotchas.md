---
gist: "Read when: benchmarking models, a model's latency is unexpectedly high, or JSON parsing sees inline think tags."
---

# Thinking tokens and benchmark gotchas

- 2026-10-09 — Thinking: thinking-capable Ollama models (gemma4, qwen3.5, lfm2.5) emit hidden reasoning tokens that multiply latency (gemma4:26b made ~2,300 output tokens before a short tool call). `agents/backends.py` now sends `think: false` for models that advertise the capability unless OLLAMA_THINK=true; thinking is logged at TRACE when on. Earlier Gemma timings in these notes were measured with thinking ON.
- 2026-10-09 — Gotchas found while benchmarking: (1) `ollama run <model> "prompt"` waits forever on stdin when stdin is not a terminal; add `< /dev/null`. (2) Lfm2.5 puts `<think>...</think>` inline in the content; `agents/runner.py` strips it (and logs it at TRACE) before parsing JSON. (3) Even with a fixed seed, GPU runs are not bit-identical (same cell scored 70 and 85). (4) A scorer must score an empty answer as 0, or failures look like 50%. (5) ministral-3's malformed tool call makes Ollama return HTTP 500; the runner falls back to the harness.
