---
id: 06-validate-and-close
status: done
depends_on: [05-narrative-report]
touches:
  - tests/test_anthropic_live_parity.py
  - tests/test_anthropic_live_accounting.py
  - usage/anthropic-api-ledger.jsonl
  - plans/archive/response-templates/results.md
  - plans/archive/live-parity/exception-record.md
  - README.md
  - memory/narrate-only-and-grounding-guards.md
lane: validate
gate: python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R6, R7]
evidence: "2026-11-07: Offline: python3 -m unittest discover -s tests -> 532 tests OK (5 skipped as before), check_context ok, check_plan ok, RUN_LIVE_* unset (run immediately before the live run; the README and memory edits and results.md after it only needed check_context, rerun below). Removed TOLERATED_TRUNCATION, the tolerated record/summary keys and the test that pinned it; the narrative-truncation tests now assert a truncated narrative fails like any role; exception 1 marked CLOSED in plans/archive/live-parity/exception-record.md. Spending preflight: pricing page rechecked 2026-11-07 (Haiku 5.5 0.10/0.50 USD per million up to 100k prompt tokens, 5x above, 1h cache write 2x, US inference 1.1x; matches the estimator; the page states no date); Denver date equals PRICE_CHECKED; estimator estimate for 65 attempts, 100000 input, 16384 output = USD 2.015728; the gate's live_run then reserved that amount in usage/anthropic-api-ledger.jsonl before the first request (guard: zero SDK retries, 120 s timeout, request and input-byte caps). JIM'S DECISION 2026-11-07: the reservation (2.015728) exceeds the plan bound of USD 0.50 (even the minimum 20 requests reserve 0.62); he chose to reserve the gate's worst case and treat USD 0.50 as the cap on settled spend. Live: RUN_LIVE_ANTHROPIC_PARITY=1 python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v -> 1 test OK, not skipped, 133.7 s; 29 requests, 295123 input and 32694 output tokens; settled from API usage at USD 0.05044523 (under 0.50; reservation not retained); 20 of 20 role/phase runs narrative_source model, no fallback, no failed check; narrative role 1 request, 316 and 411 output tokens (was 16384, truncated), not_truncated passed with no tolerance. Ledger after: spent 0.41837642, held 0.0400224 (earlier interrupted diagnostic), remaining 19.54. plans/archive/response-templates/results.md written (before/after tokens, cost and latency per role, narrative before/after, word counts, caveats). README gained operator notes for templates and the report; memory/narrate-only-and-grounding-guards.md gained a dated entry. Not verified: examiner-paragraph source per role is not recorded by the gate (inferred from the request count: a rejected paragraph would add a retry request, and there were none); only 4 of 9 roles had findings on sample_loan.json; no OpenAI live run (not authorized), so no-truncation on OpenAI rests on the 150-word limit. Ledger rows untouched; no commit or push. JIM'S DECISION 2026-11-07 on process deviations: accepted both. (a) goal.md rule 3 (test before code) was not followed for steps 01, 02, 04 and 05 (step 03 was test-first); tests were added afterwards and mutation-checked. (b) goal.md rule 5: the estimate was run by hand but the single durable reservation was made by the gate's own live_run (the same estimator.reserve call) rather than a separate manual reserve, which would have double-held USD 2.02."
---

# Run the combined validation, retire the truncation tolerance and prove it live once

Write for an agent with no chat history.

## Change

- Remove `TOLERATED_TRUNCATION` and the test that pins it (R6 names this as the permitted exception to the protected-check rule). Mark exception 1 closed in the archived record with the date and the reason.
- Preflight: `anthropic_cost_estimator.py estimate` then `reserve`; recheck rates and date. Run `RUN_LIVE_ANTHROPIC_PARITY=1 python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v` once. The narrative role must pass `not_truncated` with no tolerance, and every role must still be `model` or `model_retry`.
- Write `plans/archive/response-templates/results.md`: tokens and cost per role before (archived results) and after, word counts per regime, and any role that fell back to code paragraphs.
- README: operator notes for `templates`. Update the memory topic only if a non-obvious finding appears.

## Do not change

Rules, packs, other plans' files, existing ledger rows. No OpenAI live run.

## Dependencies already satisfied

- 05-narrative-report: the new report; all earlier steps.

## Completion criteria

Full offline suite, context and plan checks pass with `RUN_LIVE_*` unset. The live gate passes non-skipped with no tolerance. Reservation settled from API usage or retained with a reason.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
