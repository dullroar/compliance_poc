---
id: 02-bar-and-sweep
status: done
depends_on: [01-candidates-and-guard]
touches:
  - benchmarks/floor_bar.py
  - benchmarks/floor_sweep.py
  - tests/test_floor_bar.py
  - plans/archive/tune-ais/scenarios.md
lane: sweep
gate: python3 -m unittest tests.test_floor_bar -v && python3 -m benchmarks.floor_sweep --dry-run
requirements: [R2, R3, R4, R6]
evidence: "JIM CONFIRMED 2026-11-07 (answers to four questions in the session): (1) bar and T5 as encoded: T1-T4, 90% first-pass over scenarios x 2 modes x 3 reps, a paragraph rewritten by code after the retry counts as a model failure, T5 = 12 paragraphs (hmda 4, one each from the 8 other roles with paragraphs, narrative excluded); (2) the 16 scenarios as listed in plans/archive/tune-ais/scenarios.md, missing cases (hvcre fail, ybs fail, trid gap) recorded as not tested; (3) rung 1 runs ONLY for roles that fail rung 0 (literal R3), so --rung1 needed is now the default; (4) the auditor's repeated-rule-id problem is recorded as a finding (its model rungs cannot clear fail:all and gap:all whatever the model), no runtime change. 2026-11-07, BUILT, AWAITING JIM'S CONFIRMATION (the step's stop; step 03 must not start before it). Gate: python3 -m unittest tests.test_floor_bar -> 41 tests OK (about 75 s); python3 -m benchmarks.floor_sweep --dry-run -> exit 0, prints the 10-role table (about 22 s, no network, no credentials, no spend); full suite python3 -m unittest discover -s tests -> 625 tests OK (6 skipped, RUN_LIVE_* unset); check_context.py and check_plan.py ok. Built: benchmarks/floor_bar.py (T1-T4, first-pass rule, setting verdict over the full grid, lowest passing rung, T5 sample chooser; pure, no I/O; limits imported from compliance_common.templates, not copied), benchmarks/floor_sweep.py (scenario chooser, rungs 0-2, per-role climb, metadata-only run file, --dry-run with fake backends, table in the floor.md layout, --scenarios-md; --live refuses until step 03), plans/archive/tune-ais/scenarios.md (generated), tests/test_floor_bar.py (bar tests incl. a must-fail record for every failure kind and for every sheet-item limit, a T5 seed bug found and fixed by them, and sweep tests: climb, skips with reasons, rung 0 asks no model, grid size, width honored, truncation fails T2, run file has no texts). Dry-run result with cooperative fake models: 9 of 10 roles (hmda ecoa hvcre hpml trid fzd ybs vmi narrative) clear rung 0 (code only) and rung 1; the auditor clears rung 0 but not rung 1 (T4 x12 of 18 runs) - see the finding below; T5 sample = 12 paragraphs (hmda 4, one each from ecoa hvcre hpml trid fzd ybs vmi auditor). WHAT JIM MUST CONFIRM OR DECIDE: (1) the bar as encoded, in particular these readings of the spec, which are mine: (a) rung 0 passes T1 by construction because no model is asked, so code alone is scored on T2-T4 and will clear for most roles, which would make the floor 'no model' for them (spec Domain challenge item 2); (b) R3 says a role stops at its first passing rung, step 03 says run rung 1 for all roles; the sweep runs rung 1 for all by default (about USD 0.5 of Haiku) and --rung1 needed gives the literal R3: which one; (c) T4 counts a paragraph that code rewrote after the model's one retry as a failure of the model rung; (d) roles = 8 domain + auditor + narrative, the narrative role's T4 is its summary (plain, grounded, at most 150 words, model-written) and it is not in the T5 sample; (e) T5 = 12 paragraphs, hmda 4 and one from each other role with paragraphs (8), chosen by hash of a fixed seed from the cheapest passing rung, so at rung 0 you would be reading code-written text. (2) The scenarios in plans/archive/tune-ais/scenarios.md (16): the spec names tests/fixtures/*/scenarios.json but only YBS has one, so cases come from the response-templates fixtures; HVCRE and YBS have no failing case and TRID no gap case in the fixtures, so those roles run 2 scenarios not 3; the auditor and narrative role run sample, fail:all and gap:all, with their inputs built by code only. (3) FINDING, not a lowered bar: the auditor can never clear a model rung on fail:all and gap:all whatever the model, because the runtime matches model paragraphs by rule id and the auditor writes AUD-PRICING and AUD-DATES twice each, so check_paragraphs rejects 'more than one paragraph' and code rewrites them (reproduced with a fake that echoes the drafts exactly). Fixing agents/runner.py is outside this plan's delegated authority; options: record it as the auditor's finding (it clears rung 0 anyway), fix the matching in a separate change, or drop those two scenarios from the model rungs. Cost outlook for step 03 (from the archive, about USD 0.0017 per Haiku request): rung 1 for all 10 roles is about 306 requests, about USD 0.5; Sonnet 5.5 is about 20 times that per request, so one role at rung 2 (18 runs, about 36 requests) is about USD 1.2 and the USD 5 bound allows about three such roles; reserve before each run; stop and escalate if more are needed. Not done by design: no live call, no reservation, no change to agents.yaml, the runner, prompts or the ledger. Deviation: the sweep tests live in tests/test_floor_bar.py (inside the touches list) rather than a second test file."
---

# Encode the bar and the ladder, runnable offline with fakes

Write for an agent with no chat history.

## Change

- `floor_bar.py`: T1-T4 and the first-pass rule as pure functions over run records, with tests that must fail for each failure kind.
- `floor_sweep.py`: scenarios chosen by script and listed in `scenarios.md`; rungs 0-2; per-role climb and stop; a metadata-only run file; `--dry-run` with fake backends; a table matching the `floor.md` layout.
- **Stop and ask Jim to confirm the bar (R2), the scenarios, and the T5 sample size before step 03.**

## Do not change

Runtime code, prompts, ledgers.

## Dependencies already satisfied

- 01: candidates run and are priced.

## Completion criteria

Dry-run produces the full table. Bar tests pass. Jim's confirmation is recorded in the evidence.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
