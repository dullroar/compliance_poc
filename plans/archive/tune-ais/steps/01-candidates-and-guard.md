---
id: 01-candidates-and-guard
status: done
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
  - plans/archive/tune-ais/facts.md
lane: candidates
gate: python3 -m unittest tests.test_anthropic_cost_estimator tests.test_anthropic_live_accounting tests.test_anthropic_backend tests.test_agent_runner -v
requirements: [R1, R6]
evidence: "2026-11-07: tests written first and seen red (ImportError on the new names; 12 estimator errors), then green. Gate modules (tests.test_anthropic_cost_estimator, test_anthropic_live_accounting, test_anthropic_backend, test_agent_runner) -> 93 tests OK with PYTHONPATH=tests; the gate command exactly as written fails at import ('No module named live_parity_common' / 'test_ybs_evaluator') because tests/ is not a package, which was already so before this step; discover -s tests works. Full suite: python3 -m unittest discover -s tests -> 584 tests OK (6 skipped, RUN_LIVE_* unset); check_context.py and check_plan.py ok. No live call was made in this step. facts.md (dated 2026-11-07, sources and what was verbatim vs summarized): all spec facts confirmed, none differ, no escalation. Prices Haiku 5.5 0.10/0.50 (5x above 100,000 prompt tokens), Sonnet 5.5 2/10, Opus 5.5 4/20, Haiku 4.5 1/5, Sonnet 4.6 3/15, Fable 5.1 10/50 from the pricing table; forced tool_choice tool/any returns 400 on Opus 5.5, Sonnet 5.5, Fable 5.1 (and Mythos 5.1), not on Haiku 5.5, auto and none still work; thinking adaptive and effort accepted on all four, defaults high/medium. UNVERIFIED: how thinking tokens are billed (the pricing page is silent; reasoned from usage.output_tokens and the shared max_tokens cap; the live diagnostic's reported usage is the check). Haiku 4.5 is listed Active (not retired); excluded by the spec for price. Code: compliance_common/tools.py: rejects_forced_tool_choice(model) (exact ids claude-sonnet-5-5, claude-opus-5-5, claude-fable-5-1, claude-mythos-5-1, optional -YYYYMMDD) and tool_first_instruction(name); run_anthropic_tool_loop sends auto plus the instruction appended to the system prompt (never inside it) on every request for those models, and keeps the forced first call for every other model. agents/backends.py not changed. Haiku 5.5 request bodies pinned byte for byte: the first, second and seeded request bodies captured from the pre-change code are literals in tests/test_anthropic_backend.py and compared exactly. Estimator: estimate/reserve/CLI gain thinking_tokens (default 0, counted at the output rate, int >= 0, output+thinking <= 128000; the reservation row records thinking_tokens_per_attempt only when > 0, so existing rows and bounds are unchanged); rates and PRICE_CHECKED (2026-11-07) confirmed, no change needed; tests per candidate (Haiku 5.5 incl. the 5x tier, Sonnet 5.5, Opus 5.5, Sonnet 4.6) and unsupported models (Haiku 4.5, Fable 5.1, others) still refused. Live guard (tests/test_anthropic_live_parity.py): ALLOWED_MODELS = (claude-haiku-5-5, claude-sonnet-5-5); GuardedAnthropic refuses any other model at construction ('not an allowed model': Opus 5.5, Fable 5.1, Haiku 4.5, Sonnet 4.6, near-miss ids, empty) and any request carrying the other candidate's id ('unexpected model'); it refuses a forced tool_choice for Sonnet before it leaves; usage_cost(usage, model) prices at the model that ran (default Haiku, existing calls unchanged). ScriptedProvider (tests/live_parity_common.py) now answers a forced choice for a rejecting model with HTTP 400 (recorded in .rejected) and calls the tool when told by name; a Sonnet 5.5 registry run in model mode completes with every tool call by 'model' and zero 400s, and when the fake model ignores the instruction the harness covers it (by: harness) within the per-role request bound. Not done here by design: live_run still reserves and runs Haiku only (a full-registry Sonnet reservation would exceed the USD 5 per-run ceiling, so the sweep reserves per role in step 03); the first live call of each new model is a one-request diagnostic in step 03; Sonnet 5.5 behavior under the instruction is therefore verified against a fake, not the real API, until then."
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
