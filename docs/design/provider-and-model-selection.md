---
gist: "Read when: adding a provider, changing the default model or COMPLIANCE_MODEL, or assigning models by role."
---

# Provider handling and model selection

- Provider handling is intentionally small: Anthropic, local Ollama, and optional OpenAI expose the same runtime-narration interface; Ollama uses its native HTTP API to avoid a second local-provider dependency. The default provider remains Anthropic and the local Ollama default is `gemma4:26b`. `COMPLIANCE_MODEL` and the CLI `--model` option remain explicit overrides for reproducible alternative-model runs; OpenAI requires one of them because no OpenAI default model is selected.
- Provider and model selection change narration quality, cost, latency, and the data path—not compliance outcomes. Evaluators own domain outcomes; the auditor's deterministic evaluator owns cross-regime findings. Model-specific differences belong in the prose and report, so models may be assigned by role (domain agent versus synthesis) and compared against the same deterministic records.
- OpenAI is a runtime-only provider. The builders retain their existing provider scope and do not gain OpenAI support from this selection; a separate plan would be required to change that boundary.
- Remote narration begins with synthetic or de-identified inputs. Setting `store: false` on a Responses request limits application state handling where supported; it does not replace owner approval and data-handling review for non-synthetic records.
