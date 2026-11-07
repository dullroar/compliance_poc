---
id: 04-anthropic-live
status: done
depends_on: [02-anthropic-harness]
touches:
  - usage/anthropic-api-ledger.jsonl
  - plans/live-parity/runs-anthropic.jsonl
lane: anthropic-live
gate: RUN_LIVE_ANTHROPIC_PARITY=1 python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v
requirements: [R1, R2, R3]
evidence: "2026-11-07 DONE. Gate `RUN_LIVE_ANTHROPIC_PARITY=1 python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v` passed non-skipped (Ran 1 test OK, 233.4 s; Python 3.12.3, anthropic SDK 0.109.1, claude-haiku-5-5, standard tier). Run e0b37313116b4a8198e10fe06d14c7bc: 29 requests of cap 65, 232.2 s, 341448 input and 55210 output tokens, no cache tokens, no refusals, no retries, usage reported for every request; reservation 2.015728 settled from API usage at USD 0.06792478. 20 of 20 role/phase narratives succeeded, all narrative_source=model with a single guard attempt (8 domain roles, auditor, narrative role, in the model and seeded phases); decision parity, canonical arguments, provenance (by=model in the model phase, by=seeded in the seeded phase), schema validity and ordering passed everywhere; cost per successful narrative USD 0.003396239. The narrative role is recorded as tolerated truncation (stopped at the 16384 output cap in both phases): tolerated violation 1 in exception-record.md, review by 2026-12-07. Path to green, 5 live runs in total, USD 0.3679 spent of 20 with 0.0400224 still held by an interrupted diagnostic reservation (request status unknown, retained): (1) thinking consumed the 8192 cap, fixed with output_config.effort=low for the Claude 5 family (compliance_common/tools.py) after Jim approved a provider-default change; (2) the narrative report is longer than the cap, cap raised to 16384 for Anthropic only (ANTHROPIC_MAX_TOKENS), remaining truncation tolerated by Jim; (3) the auditor fell back in 3 of 8 earlier role/phase runs because contradicts_result flagged its cross-regime narrative (it must say other regimes are compliant): with Jim's approval the 'claims compliance' check is skipped for the auditor only (cross_regime, agents/runner.py), with offline regression tests written first; every other role and the Compliant-result check are unchanged. Earlier runs are retained in runs-anthropic.jsonl and the ledger."
---

# Run the registry-wide live parity test on claude-haiku-5-5

## Change

- Precondition: the ledger holds a `baseline_verified` row. If it does not, set `status: blocked` and ask Jim for an owner-confirmed amount. Do not guess, and do not touch the OpenAI lane. After Jim states the amount, record it with `python3 scripts/anthropic_cost_estimator.py baseline --prior-usd <amount> --source owner-confirmed` and continue.
- Verify the PRICE date, run `python3 scripts/anthropic_cost_estimator.py estimate --model claude-haiku-5-5 --attempts <N> --input-tokens <bytes bound> --output-tokens 8192`, confirm that it fits, then run the gate. Both phases are in one run. Repeat only after in-scope diagnosis and only if the new bound fits.
- This step edits no runtime code. A defect in shared runtime goes to step 06 as a finding.

## Do not change

Source, prompts, tests, the estimator, existing ledger rows.

## Dependencies already satisfied

- 02-anthropic-harness: the guarded, offline-tested live module.

## Completion criteria

Non-skipped pass (R2: every role, both phases, no fallback). The reservation is settled from API usage or retained with a stated reason. `runs-anthropic.jsonl` holds the per-role and per-phase usage and cost table. No secrets or raw bodies recorded.

## Record

Command, versions, elapsed time, request count, token totals, reservation and settlement, per-role outcomes, cost per successful narrative, result. Retain failed runs and their reservations.
