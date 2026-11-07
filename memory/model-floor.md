---
gist: "Read when: deciding which Claude model or setting a role needs, or before changing agents.yaml models or templates, or when the model floor report may be out of date."
---

# Model floor (Anthropic)

On the synthetic workload, code alone (no model request) clears the tune-ais quality bar for all ten roles. With the model kept only for the narrative (`templates: code`), Haiku 5.5 clears it for 7 roles (hmda, ecoa, hvcre, hpml, trid, fzd, ybs) and not for vmi (retries on gap cases), the auditor (one fallback) or the narrative role (invented numbers in 3 of 18 summaries); the full numbers and caveats are in `plans/archive/tune-ais/floor.md`. Do not read the first sentence as "turn the model off": no `agents.yaml` setting does it. Facts that cost time: Sonnet 5.5, Opus 5.5 and Fable 5.1 return a 400 on a forced `tool_choice` (the code sends `auto` plus an instruction naming the tool for them); the auditor can never get model-written paragraphs on cross-regime cases under `templates: model` because its rule ids repeat; the reservation for a full Haiku registry run is about USD 2 but the spend about USD 0.05. Re-run offline with `python3 -m benchmarks.floor_sweep --dry-run`, live with the commands in the report (diagnostics about USD 0.01, the Haiku rung about USD 0.40). Measured 2026-11-07; distrust after 2027-02-07 or when prices, models or the templates change.
