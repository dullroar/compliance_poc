---
id: 01-candidates-and-guard
status: pending
depends_on: []
touches:
  - compliance_common/tools.py
  - agents/backends.py
  - scripts/anthropic_cost_estimator.py
  - tests/test_anthropic_cost_estimator.py
  - tests/test_anthropic_backend.py
  - tests/live_parity_common.py
  - tests/test_anthropic_live_accounting.py
  - tests/test_anthropic_live_parity.py
  - plans/tune-ais/facts.md
lane: candidates
gate: python3 -m unittest tests.test_anthropic_cost_estimator tests.test_anthropic_live_accounting tests.test_anthropic_backend tests.test_agent_runner -v
requirements: [R1, R6]
evidence: ""
---

# Verify the vendor facts, then let candidate models run the same path, priced and guarded

Write for an agent with no chat history.

## Change

- Re-verify every model fact in the spec's Goal section against the vendor documentation. Record sources and the date in `facts.md`.
- Model mode without forced `tool_choice` for models that reject it; Haiku 5.5 request bodies stay byte-for-byte unchanged (test it). Keep forced choice for Haiku 5.5 unless step 03's diagnostic shows a 400.
- Estimator: confirm rates and `PRICE_CHECKED` for Haiku 5.5 and Sonnet 5.5; count thinking tokens as output; test each candidate.
- Live guard: admit the candidate ids and refuse everything else. Offline tests first. No live call in this step.

## Do not change

Thinking and effort settings, caps, ledgers' existing rows, prompts, rules.

## Dependencies already satisfied

- None.

## Completion criteria

Offline tests pass for request shape, estimator and guard refusals. `facts.md` is dated.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
