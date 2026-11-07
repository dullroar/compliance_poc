---
id: 02-anthropic-harness
status: done
depends_on: [01-live-foundations]
touches:
  - tests/test_anthropic_live_parity.py
  - tests/test_anthropic_live_accounting.py
lane: anthropic-harness
gate: python3 -m unittest discover -s tests -p test_anthropic_live_accounting.py -v && python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v
requirements: [R1, R2, R3, R4]
evidence: "2026-11-06. Gate `python3 -m unittest discover -s tests -p test_anthropic_live_accounting.py -v && python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v` passed: accounting 23 tests OK; live module OK (skipped=1) with RUN_LIVE_* unset. Python 3.12.3 (.venv), anthropic 0.109.1. tests/test_anthropic_live_parity.py: GuardedAnthropic (zero SDK retries and finite timeout required at construction; per-run cap = derived total 65, per-role cap from step 01; 100000-byte UTF-8 input bound; max_tokens == 8192; model claude-haiku-5-5; one tool per role and tool_choice allow-list; repository system prompt; standard tier injected via service_tier=standard_only; fields allow-list excludes stream/thinking/hosted tools; refusals raise GuardRefusal, not RuntimeError, so the runner cannot turn them into a fallback), live_run (price-date check, estimator reserve once per run with 65 attempts x 100000 x 8192 = USD 1.722864 < 5, settle from reported usage under the estimator's conservative cache and US-premium assumptions, or retain the whole reservation when any usage is missing, odd, non-standard-tier or a request errored), RunFile metadata rows (reservation, request_start before send, request_outcome, refusal, run_summary with per-role/phase and per-run cost table and cost per successful narrative). tests/test_anthropic_live_accounting.py: every cap and refusal (no request leaves), exact byte bound, retries and timeout, one reservation and one settlement <= reservation, unknown/odd usage retains reservation with null costs, failed request retained, no double counting, cumulative cap, unknown baseline, stale price date, missing ledger, crash durability and replay equality, no credentials or bodies in files, default skip. Offline outbound inspection (recording fake through the guard): per-role maxima 11-73 KB (see step 01), all under 100000. usage/anthropic-api-ledger.jsonl unchanged (1 row, baseline_unknown); no run file written. Step 04 remains blocked on an owner-confirmed baseline."
---

# Build the guarded, opt-in Anthropic live run (offline-tested)

## Change

- `tests/test_anthropic_live_parity.py`: a skipped-unless-`RUN_LIVE_ANTHROPIC_PARITY=1` test using `claude-haiku-5-5` and the step-01 driver. It builds `anthropic.Anthropic(max_retries=0, timeout=<finite>)` and injects a wrapped client into `Backend`. The wrapper enforces the request cap, the input-byte bound (at most 100,000), `max_tokens`, model and tool allow-list. Before the first request it calls the estimator's `reserve` once (the bound covers every attempt, for example 80 x 100k input / 8192 output), and afterward `settle` with a cost computed from reported usage, or leaves the reservation if usage is missing. It writes a metadata-only run summary to `plans/live-parity/runs-anthropic.jsonl`.
- `tests/test_anthropic_live_accounting.py`: offline tests (temporary ledgers, fake SDK) for each cap, zero SDK retries, unknown usage keeping the reservation, settlement at or below the reservation, a refused `reserve` when the baseline is unknown or the budget is short, restart durability, and no raw bodies or secrets in any file.
- Perform the outbound-payload inspection offline with a recording fake and report the per-role sizes.

## Do not change

`scripts/anthropic_cost_estimator.py` semantics, `usage/anthropic-api-ledger.jsonl` (no writes in this step), `agents/**`, existing tests.

## Dependencies already satisfied

- 01-live-foundations: the driver and the derived bounds.

## Completion criteria

The gate passes with the live module skipped explicitly. All caps and the failure paths are proven offline. No API call was made.

## Record

Date, commands, results, interpreter and SDK versions.
