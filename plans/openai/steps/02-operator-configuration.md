---
id: 02-operator-configuration
status: done
depends_on: []
touches:
  - README.md
  - agents.yaml
  - docs/design/provider-and-model-selection.md
lane: operator-documentation
gate: python3 scripts/check_context.py
requirements: [R1, R3]
evidence: "2026-11-06: python3 scripts/check_context.py passed (build_context_indexes.py, check_plan.py, check_links.py, and scan_context_secrets.py)."
---

# Document safe OpenAI selection without changing the repository default

Describe OpenAI as an optional runtime narrator and provide a reproducible mixed-provider configuration.

## Change

- `README.md`: add a concise OpenAI setup block, required environment variables, separate API-billing note, no-real-records-first boundary, and examples for global replacement and per-agent mixed use.
- `agents.yaml`: update only explanatory comments to list `openai` and describe `seeded` as the preferred mode for a remote narrator; retain all existing runtime entries and defaults.
- `docs/design/provider-and-model-selection.md`: explain that provider/model choice changes narration quality, cost, latency, and data path—not deterministic compliance outcomes—and that the builder scope remains separate.

## Do not change

- Existing default provider/model values, agent URLs, concurrency, prompts/specs, or builder configuration.
- Do not include keys, account identifiers, personal paths, or live-record examples.

## Dependencies already satisfied

- None. This documentation is written to the agreed specification, independently of the provider implementation.

## Completion criteria

- An operator can configure OpenAI globally or for only `auditor`/`narrative` without guessing variable names or assuming DigitalOcean infrastructure.
- The documentation states that `store: false` is not a substitute for an approved data-handling decision.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
