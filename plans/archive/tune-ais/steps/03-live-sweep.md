---
id: 03-live-sweep
status: done
depends_on: [02-bar-and-sweep]
touches:
  - usage/anthropic-api-ledger.jsonl
  - plans/archive/tune-ais/runs-anthropic.jsonl
lane: live
gate: python3 -m benchmarks.floor_sweep --live --provider anthropic
requirements: [R1, R2, R3, R5]
evidence: "2026-11-07: python3 -m benchmarks.floor_sweep --live --provider anthropic -> exit 0. Preflight: spec approved and Jim's confirmation of the bar, scenarios and rung-1 rule recorded in step 02; ANTHROPIC_API_KEY present in .env (name only); synthetic sample_loan.json only; rates and date rechecked 2026-11-07 (plans/archive/tune-ais/facts.md; PRICE_CHECKED 2026-11-07); anthropic_cost_estimator.py estimate then reserve inside the diagnostic: claude-haiku-5-5 1 attempt, 100000 input bytes, 16384 output tokens -> USD 0.0310112; claude-sonnet-5-5 same bounds -> USD 0.620224; zero SDK retries, 120 s timeout, request limit 1 and one allowed model per guard; runs sequential on one ledger. Result: rung 0 (code only) scored by the bar for all 10 roles on 27 offline runs: every role clears T1-T4 with first-pass 100%, so under Jim's rule (rung 1 only where rung 0 fails) NO role needed rung 1 or 2 and no sweep request was made; every role has a verdict for every rung tried (rung 0) and a recorded reason for the skipped rungs (plans/archive/tune-ais/runs-anthropic.jsonl: 1 sweep_start, 27 run, 10 verdict, 10 ladder rows; committed, with a .gitignore exception like the other archived run files). One-request diagnostics (as step 03 requires): Haiku 5.5 with the forced tool choice -> tool_choice 'tool' accepted, stop_reason tool_use, content blocks [tool_use], 2430 in / 176 out tokens, settled USD 0.0003641, reservation 66e5189fa74c435e8ee362f92eaec98d; Sonnet 5.5 in model mode (auto plus the instruction naming the tool, no forced choice) -> NO 400, the model called the tool, stop_reason tool_use, blocks [tool_use], 2343 in / 164 out, settled USD 0.0069586, reservation 9560e365a82e4e5dae331cccd65c32dc. Both settled from API usage; ledger after: spent USD 0.63289281, held USD 0.0400224 (the earlier retained diagnostic), remaining USD 19.327. Plan spend USD 0.0073 against the USD 5 bound (reservations were USD 0.031 and 0.620, one at a time, under the USD 1.50 per-run limit). Gaps: thinking-token billing stays UNVERIFIED (neither response contained a visible thinking block and usage does not split thinking out of output_tokens); Haiku 5.5 forced choice is confirmed live twice (here and in the parallelize ramp); Sonnet 5.5 behavior beyond one request was not exercised because no role needs rung 2; OpenAI not touched. The auditor's model-rung limitation (repeated rule ids) was not exercised live for the same reason and stays a recorded finding. Offline: python3 -m unittest tests.test_floor_bar -> 47 tests OK. FOLLOW-UP, authorized by Jim 2026-11-07 ('Measure first, then decide'): rung 1 measured live for ALL roles as Haiku 5.5, effort low, templates: code, capped at rung 1 (Sonnet not authorized). Command: python3 -m benchmarks.floor_sweep --live --provider anthropic --climb --rung1 all --templates code --max-rung 1 --out plans/archive/tune-ais/runs-anthropic-rung1.jsonl -> exit 0. Preflight: estimate for the largest batch (36 attempts, 100000 input bytes, 16384 output tokens) USD 1.1164032 (under the USD 1.50 per-run ceiling), rates and date unchanged (PRICE_CHECKED 2026-11-07), dry run of the same configuration first, zero SDK retries, 120 s timeout, per-batch request limit, one allowed model, batches sequential on one ledger, RUN_LIVE_* unset. Result: 189 runs, 240 requests, 20 reservations each settled from API usage (no unknown usage, no budget stop), USD 0.39542382 settled; plan live spend with the diagnostics USD 0.4027 of the USD 5 bound; ledger after: spent 1.02831663, held 0.0400224, remaining 18.93. Verdicts: pass hmda ecoa hvcre hpml trid fzd ybs (first-pass 100%); FAIL vmi (every run passes T1-T4 but first-pass 78%: 4 of 18 retried, all gap:vmi), auditor (1 of 18 deterministic_fallback, gap:all seeded: T1), narrative (3 of 18 summaries rejected for an added number and rewritten by code, fail:all: T1 and T4). A failing role is a finding, not a lowered bar; rung 2 not run (rung 0 clears everywhere; Haiku-only authorization). Bar amendment recorded: under templates: code a paragraph source of 'code' is not a rewrite (benchmarks/floor_bar.py, tests/test_floor_bar.py). Code: batches with a reservation per role and tool mode, LiveBackends, per-cell truncation flag, BudgetStop; tests/test_floor_bar.py -> 52 tests OK. Not exercised live: BudgetStop paths, rung 2 batches (Sonnet's worst case per batch is over the USD 1.50 ceiling, so rung 2 would need a smaller batch plan and Jim's decision)."
---

# Run the bounded live sweep, cheapest rung first

Write for an agent with no chat history.

## Change

- Per-new-model one-request diagnostic (forced tool choice behavior on Haiku 5.5; Sonnet 5.5 model mode).
- Run rung 1 for all roles, three repetitions of each scenario in both tool modes; run rung 2 only for roles that failed rung 1. Rung 0 needs no live call but is scored by the same bar.
- Reserve before each run; settle from usage; stop before R5's bound. Record usage per request. A skip, timeout or fallback is not a pass.

## Do not change

Source, prompts, the bar, existing ledger rows.

## Dependencies already satisfied

- 02: harness and confirmed bar.

## Completion criteria

Every role has a pass or fail for every rung tried. The ledger shows reservations, settlements and a total at or under USD 5.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
