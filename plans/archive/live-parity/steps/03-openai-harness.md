---
id: 03-openai-harness
status: done
depends_on: [01-live-foundations]
touches:
  - tests/test_openai_live_parity.py
  - tests/test_openai_live_parity_accounting.py
  - tests/test_openai_live_smoke.py
  - tests/test_openai_smoke_accounting.py
  - tests/test_openai_cost_estimator.py
  - scripts/openai_cost_estimator.py
lane: openai-harness
gate: python3 -m unittest discover -s tests -p test_openai_live_parity_accounting.py -v && python3 -m unittest discover -s tests -p test_openai_live_parity.py -v && python3 -m unittest discover -s tests -p test_openai_smoke_accounting.py -v && python3 -m unittest discover -s tests -p test_openai_cost_estimator.py -v
requirements: [R1, R2, R3, R4]
evidence: "2026-11-06. Gate (four commands) passed: test_openai_live_parity_accounting.py 25 tests OK; test_openai_live_parity.py OK (skipped=1, RUN_LIVE_* unset); test_openai_smoke_accounting.py 17 OK (10 existing unchanged + 7 new); test_openai_cost_estimator.py 10 OK (4 existing unchanged + 6 new). Python 3.12.3 (.venv), openai 3.46.0. tests/test_openai_live_smoke.py: backward-compatible Ledger generalization only: start_cycle(max_requests, request_bound, input_bound_tokens, command) with validated bounds, per-cycle slots in state/start_request/end_cycle, optional role label on request_reservation and request_outcome rows, end_cycle(successes, expected_successes); defaults are the existing constants, no existing assertion, constant meaning or ledger row changed, and the archived ledger (8 rows) and generated legacy cycles replay to identical totals against a verbatim copy of the old state(). New constants PARITY_INPUT_BOUND_TOKENS=100000, PARITY_MAX_REQUESTS=80, PARITY_REQUEST_BOUND=USD 0.0617584. scripts/openai_cost_estimator.py: assess(..., profile) with 'smoke' default (still 1-6 requests) and 'parity' (1-80 requests, 100000-token input bound, reserves exactly the requested slots, per-run ceiling USD 5 and the shared cumulative cap both gate fits); CLI --profile auto picks parity above 6 requests. Preflight for 56 requests: required_cycle_reservation_usd 3.4584704, fits True, remaining 19.993459125. Unknown model, stale price, missing/unreadable ledger or unknown event still fail closed. tests/test_openai_live_parity.py: GuardedOpenAI (zero SDK retries and finite timeout required; store false; standard tier injected; max_output_tokens 8192; one model; one function per role; schema/format, tool_choice and parallel-call allow-lists; exact outbound validation for every role (instructions = repository prompt + pinned regulation text, first user turn = the narration of the synthetic fixture, structural check for the auditor/narrative roles, seeded exchange = canonical case); 100000-byte input bound; run cap 56 and per-role caps; durable ledger request_reservation before every send; sanitized failures), live_run (assess preflight, full-cycle reservation in the shared ledger before the first request, per-role/phase/run cost table replayable from ledger rows, run summary in plans/live-parity/runs-openai.jsonl), rehearse() (the complete run through the guard against the offline recording fake before any live request). tests/test_openai_live_parity_accounting.py: 25 offline proofs of validation, each cap and refusal, reservation-before-send, byte bound, failed requests, unknown/inconsistent/non-standard-tier usage retaining reservations, aggregation and replay, shared cumulative cap, restart recovery, fail-closed preconditions, no credentials/bodies in files, default skip. Also: a fidelity fix to the step-01 recording fake (OpenAI responses now report service_tier default and the full usage breakdown the real API returns); step 01 and 02 suites re-run green. plans/archive/openai-smoketest/runs.jsonl (8 rows) and usage/anthropic-api-ledger.jsonl unchanged; no run file written."
---

# Generalize the OpenAI guard and ledger for a registry-wide run (offline-tested)

## Change

- `tests/test_openai_live_smoke.py`: a backward-compatible generalization of `Ledger` only. A `cycle_reservation` may carry its own `max_requests`, `request_bound_usd` and `input_bound_tokens`; legacy rows default to the existing constants and replay to identical totals. Optional `role` labels are added to request rows. No existing assertion, constant meaning or ledger row changes.
- `scripts/openai_cost_estimator.py` and its test: accept the new request count (up to the step-01 total, at most 80) and report the new cycle bound; keep failing closed on unknown models, stale prices or an unreadable ledger.
- `tests/test_openai_live_parity.py`: a skipped-unless-`RUN_LIVE_OPENAI_PARITY=1` test using `gpt-6-luna` and the step-01 driver, with `max_retries=0`, a finite timeout, `store: false`, standard tier, `max_output_tokens=8192`, the input-byte bound (at most 100,000), and the outbound-payload validation pattern from the smoke test, applied to every role. It reserves the full cycle before the first request, and it writes a metadata-only run summary to `plans/live-parity/runs-openai.jsonl`.
- `tests/test_openai_live_parity_accounting.py` and additions in `tests/test_openai_smoke_accounting.py`: offline proofs of the caps, per-role and per-phase aggregation, restart recovery, missing usage, the shared cumulative cap, and old-versus-new ledger replay.

## Do not change

Existing assertions in any test; existing rows of `plans/archive/openai-smoketest/runs.jsonl`; `agents/**`.

## Dependencies already satisfied

- 01-live-foundations: the driver and the derived bounds.

## Completion criteria

The gate passes with the live module skipped. The existing smoke and estimator tests pass unmodified apart from additions. The preflight `python3 scripts/openai_cost_estimator.py --model gpt-6-luna --requests <N>` prints a bound that fits the remaining budget.

## Record

Date, commands, results, SDK versions, the preflight output.
