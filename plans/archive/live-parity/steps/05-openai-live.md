---
id: 05-openai-live
status: done
depends_on: [03-openai-harness]
touches:
  - plans/archive/openai-smoketest/runs.jsonl
  - plans/live-parity/runs-openai.jsonl
lane: openai-live
gate: RUN_LIVE_OPENAI_PARITY=1 python3 -m unittest discover -s tests -p test_openai_live_parity.py -v
requirements: [R1, R2, R3]
evidence: "2026-11-06 (run 2026-11-07T03:58:14Z-04:03:19Z UTC), gate `RUN_LIVE_OPENAI_PARITY=1 python3 -m unittest discover -s tests -p test_openai_live_parity.py -v` exit 0, 1 test, not skipped. Python 3.12.3 (.venv), openai 3.46.0, model gpt-6-luna, standard tier, store false, max_retries 0, timeout 120 s. Preflight before the run: `python3 scripts/openai_cost_estimator.py --model gpt-6-luna --requests 56` -> profile parity, required_cycle_reservation_usd 3.4584704, remaining 19.993459125, fits True; pricing https://developers.openai.com/api/docs/models/gpt-6-luna checked 2026-11-06 (= today). Credentials by name only (OPENAI_API_KEY); data: sample_loan.json-derived cases, repository prompts and pinned regulation text only; the offline rehearsal through the guard and validator passed first. Cycle b627b161cd854596888788db29eacdc1: reservation 56 slots x 0.0617584 = 3.4584704 written to the shared ledger before the first request; 30 requests sent (cap 56), 0 refusals, 0 SDK retries, 0 failures; cycle_end released the 26 unused slots; reserved afterwards 0. Ledger plans/archive/openai-smoketest/runs.jsonl is append-only (62 rows added, 0 removed or changed); run metadata appended to plans/live-parity/runs-openai.jsonl (32 rows). Elapsed 301.978 s (model phase 165.2 s, seeded 136.8 s). Outcomes: all 20 role/phase runs (8 domains + auditor + narrative, model and seeded) passed every check: decision parity with direct evaluation on the exact payload, canonical arguments, tool provenance (model phase by=model for all 9 tool roles, seeded by=seeded), schema validity, ordering, no leaked decision-owned fields. Narrative source: 19 `model`, 1 `model_retry` (auditor, model phase: guard attempts 2, 3 requests); no deterministic_fallback; no harness calls. Requests per role/phase: tool roles model 2 (auditor 3), seeded 1; narrative 1 per phase. Usage (API-reported): input 224154 (cached 101194), output 26858 (reasoning 8289, part of output), total 251012; every request reported usage and standard tier (unknown_requests 0). Conservative budget charge USD 0.145442550 for the run; cumulative incurred in the shared ledger 0.151983425 of 20. Per role/phase table is in the run_summary row of plans/live-parity/runs-openai.jsonl. Finding for step 06: the API did not report the cache-write TTL breakdown (cache_write_30m/12h tokens null, cache_write_tokens 121041), so the ledger's exact `estimated_cost_usd` and therefore `cost_per_successful_narrative_usd` are null by the existing fail-closed rule; the conservative per-narrative figure is 0.14544255 / 20 = USD 0.0072721 (a bound, not an invoice). The estimate is not an invoice; reconcile against the OpenAI billing dashboard. 2026-11-07 RERUN after the shared-runtime changes (Claude effort/cap are Anthropic-only; the auditor cross_regime guard exemption touches this path): same gate, exit 0, Ran 1 test OK, 230.5 s, run 7ec2e2710b0a40a7940312d6e55e6a85, 29 requests of cap 56, 219581 input and 24394 output tokens (6647 reasoning), conservative budget charge USD 0.1408946, 20 of 20 narratives model-sourced with no retry and no fallback (the earlier auditor model_retry did not recur); cumulative OpenAI incurred USD 0.292878025 of 20, no reservation outstanding, ledger append-only."
---

# Run the registry-wide live parity test on gpt-6-luna

## Change

- Verify the PRICE date and run `python3 scripts/openai_cost_estimator.py --model gpt-6-luna --requests <N>`, then confirm `fits: True`. Run the gate: seeded and model phases for every registry role, in one cycle under one full reservation. Repeat only after in-scope diagnosis and only if the next cycle fits the cumulative USD $20 bound.
- This step edits no runtime code. A defect in shared runtime goes to step 06 as a finding.

## Do not change

Source, prompts, tests, the estimator, existing ledger rows.

## Dependencies already satisfied

- 03-openai-harness: the generalized guard and ledger, offline-tested.

## Completion criteria

Non-skipped pass with the same R2 assertions as step 04. Ledger rows record every reservation, outcome and usage with role labels. A cycle-end row gives per-role and per-phase totals. The cumulative incurred plus reserved amount stays at or under USD $20. No secrets or raw bodies recorded.

## Record

Same fields as step 04, plus the cycle ID and the cumulative totals.
