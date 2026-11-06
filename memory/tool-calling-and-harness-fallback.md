---
gist: "Read when: a model skips or malforms its MCP tool call, a tool_calls entry shows by=harness, or choosing tool_mode for a small model."
---

# Tool calling and the harness fallback

- 2026-10-08 — Local `gemma4:26b` does not reliably call the MCP tool (it did in one live run, skipped it in the next). That is why `agents/runner.py` has a harness fallback that calls the tool and injects the result; a `tool_calls[].by == "harness"` entry is expected behavior, not a bug. The harness also overwrites the model's tool arguments with the loan payload's canonical case (logged at WARNING when they differ).
- 2026-10-09 — Tool calling by small local models: with the "tool in hand" prompt and forced-first-call logic, no model under ~9B reliably called its MCP tool itself (lfm2.5:8b, granite4.1:3b, gemma4:e4b, ministral-3:3b: harness fallback every time; qwen3.5:4b sometimes). Ministral's malformed tool call made Ollama return HTTP 500 and crashed an agent run before the runner learned to fall back. Default small local models to `tool_mode: seeded` in agents.yaml (the harness makes the call and puts it in the conversation as the agent's own first step; one model call instead of two).
