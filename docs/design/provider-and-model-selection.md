---
gist: "Read when: adding a provider, changing the default model or COMPLIANCE_MODEL, or assigning models by role."
---

# Provider handling and model selection

- Provider handling is intentionally small: Anthropic and Ollama expose the same internal message path, while Ollama uses its native HTTP API to avoid a second provider dependency. The local Ollama default is `gemma4:26b`; `COMPLIANCE_MODEL` and the CLI `--model` option remain explicit overrides for reproducible alternative-model runs.
- Model selection is a narrative-quality, latency, and resource-fit decision, not a delegation of compliance judgment. Evaluators own domain outcomes; the auditor's deterministic evaluator owns cross-regime findings. Model-specific differences belong in the prose and report, so models may be assigned by role (domain agent versus synthesis) and compared against the same deterministic records.
