---
id: 03-measure
status: done
depends_on: [01-provider-gates, 02-guard-thread-safety]
touches:
  - plans/archive/parallelize/results.md
  - plans/archive/parallelize/runs-anthropic.jsonl
  - usage/anthropic-api-ledger.jsonl
  - README.md
lane: measure
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R5, R6]
evidence: "2026-11-07: live ramp via RUN_LIVE_ANTHROPIC_PARALLEL=1 python3 -m unittest discover -s tests -p test_anthropic_live_parallel.py -k AnthropicLiveParallel -> OK (1 test, 335.7 s). Preflight before the call: spec approved; ANTHROPIC_API_KEY present in .env (name only); synthetic sample_loan.json only; pricing page refetched 2026-11-07 (Haiku 5.5 USD 0.10/0.50 per million up to 100,000 prompt tokens, 5x above, cache write 2x, read 0.1x, US 1.1x; matches the estimator, PRICE_CHECKED 2026-11-07); anthropic_cost_estimator.py estimate --model claude-haiku-5-5 --attempts 65 --input-tokens 100000 --output-tokens 16384 -> USD 2.015728 per run (under the USD 5 per-run ceiling; budget remaining USD 19.54 before); step 02 passed first; zero SDK retries and a 120 s timeout enforced by GuardedAnthropic; runs sequential on one ledger. Result: widths 1, 2, 4, 8 all clean (0 rate limits, 0 other request errors, 0 refusals, 0 role failures, 20 of 20 narratives from the model each run, no fallback); domain-phase wall time model phase 65.9, 34.6, 16.4, 14.9 s and seeded phase 43.4, 25.0, 20.2, 11.1 s (-47.5/-75.1/-77.3% and -42.4/-53.5/-74.4%); whole batch both phases 132.1, 81.0, 58.3, 61.4 s. Settled USD 0.05026692, 0.05177029, 0.05205640, 0.05310008, total 0.20719369 (bound 0.50); four reservations and four settlements in usage/anthropic-api-ledger.jsonl, ledger after: spent 0.62557011, held 0.0400224 (an earlier interrupted diagnostic, retained), remaining 19.33; per-request rows in plans/archive/parallelize/runs-anthropic.jsonl (committed, with a .gitignore exception like the archived run files). Committed remote_concurrency set to 8 (highest clean width, spec R3) in agents.yaml; the gain above width 4 is small (floor = slowest domain role, hmda). README operator note added; results.md written. Offline: tests/test_anthropic_live_parallel.py (5 offline tests: ramp, stop at first rate-limited width, spend-bound refusal before any reservation, bound rule, live class skipped by default). Combined validation: python3 -m unittest discover -s tests -> 566 tests OK (6 skipped), RUN_LIVE_* unset; check_context.py and check_plan.py ok. Deviations and gaps: (1) the step's touches list does not name tests/test_anthropic_live_parallel.py, tests/live_parity_common.py (timing capture) or agents.yaml's value; the step text requires an opt-in live timing, so I added them; (2) the live gate runs the evaluators in-process, so child-process CPU read 0.0 and the eight-subprocess start-up burst of --spawn-local was NOT measured (stated in results.md); (3) one run per width, so a few seconds of difference is noise (the width 8 model-phase auditor took 22.0 s against 8-10 s elsewhere); (4) the 429 path was never reached live, only offline; (5) the reservation per run (USD 2.015728) exceeds the plan's USD 0.50, as in the earlier approved live runs; USD 0.50 capped settled spend and was enforced by the harness between runs; (6) OpenAI not measured."
---

# Ramp the width 2, 4, 8 on Anthropic, measure, and document it

Write for an agent with no chat history.

## Change

- Add an opt-in live timing (own environment variable, off by default) that runs the sample case at width 1, then 2, 4 and 8, one run each and stopping at the first width that errors for a reason other than cost, through the production batch path, and records wall time per phase, per-role latency, tokens, cache tokens and any 429. Preflight and reserve first; settle from usage.
- Write `results.md` (table by width, percentage change, rate-limit events, CPU burst note). Set the committed `remote_concurrency` to the highest clean width. If the domain-phase gain at that width is under 25%, say so.
- README: operator note for `remote_concurrency` and `--remote-concurrency`.

## Do not change

Source behavior; ledgers' existing rows; OpenAI.

## Dependencies already satisfied

- 01 and 02.

## Completion criteria

Combined validation passes with `RUN_LIVE_*` unset. `results.md` exists with measured numbers and the settlement or the reason a reservation is retained.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
