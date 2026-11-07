---
id: 02-guard-thread-safety
status: done
depends_on: []
touches:
  - tests/live_parity_common.py
  - tests/test_anthropic_live_parity.py
  - tests/test_openai_live_parity.py
  - tests/test_anthropic_live_accounting.py
  - tests/test_openai_live_parity_accounting.py
lane: guards
gate: python3 -m unittest tests.test_anthropic_live_accounting tests.test_openai_live_parity_accounting tests.test_live_parity_common -v
requirements: [R4, R6]
evidence: "2026-11-07: python3 -m unittest discover -s tests -p 'test_*live*accounting.py' (and test_live_parity_common.py) -> test_anthropic_live_accounting 32 tests OK, test_openai_live_parity_accounting 29 OK, test_live_parity_common 19 OK; full suite 560 tests OK (5 skipped, all RUN_LIVE_* unset); check_context.py and check_plan.py ok. Existing assertions untouched (diff shows only an added import name per file). Found and fixed: (1) the guards kept role, phase and role_sent as single attributes, which mixes roles up as soon as two are in flight (a request checked against another role's prompt and allowance); they are now per call chain (RoleScoped in tests/live_parity_common.py: a context variable that asyncio.to_thread copies into the worker thread; a thread that never called begin_role sees the latest role, the serial behavior); (2) the cap check, sent and role counters, the OpenAI ledger reservation and the request_start row are now one step under the guard's lock (the request itself runs outside it), and outcome rows, costs, truncated and unknown_cost are updated under it; RunFile.append also takes an in-process lock (flock still covers other processes); (3) ScriptedProvider counts and appends under a lock and keys its decisions per call chain; _Run attributes evaluator calls per call chain; run_registry gains remote_concurrency (default unchanged: concurrency=1; the live gates are unchanged). The OpenAI ledger (tests/test_openai_live_smoke.py) needed no change: it re-reads and appends under an flock on a fresh file handle per call, which excludes threads too; proved by the stress tests. New ConcurrentGuardTests in both accounting files: with two slots left, 8 simultaneous requests -> exactly 2 proceed and 6 are refused, rows, sequences and totals exact (shared, copied-context and own-role variants, 8 rounds each); 8 threads on one role never pass its allowance; 8 roles in flight together each keep their own allowance, attribution (checked against the system prompt actually carried), sequences 1..N and cost totals (Anthropic: aggregate == guard.costs == N x 1.1 x 0.60 / 1e6); a full registry run through live_run at remote width 4 (both phases) passes every role, never exceeds a per-role bound, settles exactly and replays; 8 writers x 50 log lines to one logs/<component>.jsonl give 400 distinct valid JSON lines, and the log files written during the width-4 run parse line by line. Repeat runs of the stress tests: first batch 24 of 25 passed, 1 failed once and could not be reproduced (110 and 60 further runs: 0 failures); the likely cause was my own timing assertion (peak > 1 relied on a fixed sleep and the lock is held through a slow WSL fsync), so the first request now waits until a second is in flight; after that 70 of 70 runs passed. The failure was never captured, so the cause is inferred, not proven. Note: the red run before the fix was real for OpenAI (cap races: 8 != 4) and for the Anthropic role-attribution test; the Anthropic cap-count race did not show under the GIL, so those tests protect the lock rather than prove it was needed."
---

# Make the live request guards safe under simultaneous calls

Write for an agent with no chat history.

## Change

- Find every shared counter and every file or ledger write in the guarded clients and the shared live helper; put them under one lock.
- Add concurrent stress tests with a fake transport (cap exactness, refusal of extras, exact ledger totals, restart replay).
- Do not change cap values, models, reservations or any existing assertion. Live gates keep `concurrency=1`.

## Do not change

Existing assertions, request caps, the ledgers' rows, the estimators.

## Dependencies already satisfied

- None. Independent of 01 (no shared `touches`).

## Completion criteria

Stress tests pass repeatedly (run them at least 20 times and record the count). Existing tests pass unmodified.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
