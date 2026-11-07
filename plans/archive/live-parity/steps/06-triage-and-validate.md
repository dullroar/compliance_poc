---
id: 06-triage-and-validate
status: done
depends_on: [04-anthropic-live, 05-openai-live]
touches:
  - agents/**
  - orchestrator/**
  - compliance_common/**
  - compliance_mcp/**/adapter.py
  - compliance_mcp/**/server.py
  - tests/**
  - README.md
  - docs/design/**
  - plans/live-parity/results.md
  - plans/live-parity/spec.md
  - plans/live-parity/steps/06-triage-and-validate.md
lane: finish
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R4]
evidence: "2026-11-07, Python 3.12.3 (.venv), anthropic 0.109.1, openai 3.46.0. Triage: no shared integration defect found in decision parity, provenance or ordering; two runtime findings were repaired with Jim's approval and offline regression tests first (Claude 5 effort=low and the Anthropic 16384 output cap in compliance_common/tools.py and agents/backends.py; auditor-only cross_regime skip of the 'claims compliance' contradiction check in compliance_common/assemble.py, narrative.py and agents/runner.py), one finding is a tolerated violation (narrative role cut off at the Anthropic output cap; exception-record.md item 1, review by 2026-12-07). Both live gates were rerun on the final runtime and passed non-skipped (Anthropic run e0b37313116b4a8198e10fe06d14c7bc, OpenAI run 7ec2e2710b0a40a7940312d6e55e6a85; 20 of 20 model-sourced narratives each, no fallbacks). results.md written (side-by-side table, per role and phase, budgets, findings, not a ranking) and checked against both ledgers; README operator note added; memory/narrate-only-and-grounding-guards.md and docs/design/provider-and-model-selection.md updated. Exact combined gate with all RUN_LIVE_* unset: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py -> exit 0; Ran 436 tests OK (skipped=5, the opt-in live tests); build_context_indexes, check_plan, check_links and scan_context_secrets ok. Ledgers: plans/archive/openai-smoketest/runs.jsonl +122 lines and usage/anthropic-api-ledger.jsonl +18 lines, 0 deletions or modifications. Actual cost: Anthropic USD 0.36793119 recorded of 20 (plus USD 0.0400224 retained for an interrupted diagnostic, remaining 19.59); OpenAI USD 0.292878025 conservative of 20 (remaining 19.71). Nothing committed or pushed."
---

# Triage live findings, document results and run the combined validation

## Change

- Review the evidence from steps 04 and 05. For each demonstrated shared-runtime integration defect (not a model-quality fallback), add an offline regression test first, then repair it within the agent-parity runtime paths, then rerun the affected provider's live gate if the defect touched that path and the budget allows. If there is none, record "no defects found". Persistent narrative fallbacks are reported per role and escalated, not tuned away.
- Write `plans/live-parity/results.md` (with gist front matter): a side-by-side table per provider covering roles, phases, requests, tokens, cost, latency, narrative sources and fallbacks, and the budget remaining. State that it is not a model ranking. Add a short README operator note on the two opt-in live gates, without credentials or payloads.
- Run the exact combined validation with all `RUN_LIVE_*` variables unset. Mark the spec `complete` only if both live steps are `done` and every requirement and protected check has evidence.

## Do not change

Prompts, rules, schemas, thresholds, guard semantics, defaults, protected assertions, ledgers.

## Dependencies already satisfied

- 04-anthropic-live and 05-openai-live: both live runs and their ledgers.

## Completion criteria

The gate passes. The results document matches the ledgers. The spec status is updated. A summary of the actual cost is reported against both budgets.

## Record

Date, command, interpreter, test counts, findings and their dispositions.
