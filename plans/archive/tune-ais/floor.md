---
gist: "Read when: you need the dated Anthropic model floor (the cheapest setting per role that passes the quality bar), what it rests on, what Haiku 5.5 did under templates: code, and what it does and does not mean for agents.yaml."
---

# Model floor for Anthropic ("you must be this tall to ride")

Measured 2026-11-07 on synthetic data (`sample_loan.json` and fixture cases), plan `plans/archive/tune-ais`. **Distrust this after 2027-02-07** (inferred: about three months; earlier if Anthropic changes prices, models or the forced-`tool_choice` rules, or if prompts, rules or the response templates change). Pricing source `https://platform.claude.com/docs/en/about-claude/pricing`, checked 2026-11-07 (Haiku 5.5 USD 0.10 in / 0.50 out per million tokens, Sonnet 5.5 USD 2 / 10); vendor facts and sources in `facts.md`. The floor is for this workload and these scenarios, not production data, and is rule-based plus 12 human reads, not a compliance certification.

## Result

1. **Every role clears the bar at rung 0, code only.** Code alone writes the examiner paragraphs, the loan-officer sheet and the deterministic narrative within every limit. Under the confirmed rule (rung 1 only where rung 0 fails) no model run was needed, so no role climbed.
2. **Follow-up Jim asked for ("measure first, then decide"): rung 1 measured for every role as Haiku 5.5 at effort low with `templates: code`** (the model writes only the role's narrative; code writes the paragraphs). **7 of 10 roles clear the bar with 100% first-pass** (hmda, ecoa, hvcre, hpml, trid, fzd, ybs). **3 do not:** vmi (every run passes T1-T4 but only 78% are first-pass: 4 of 18 needed the retry, all on `gap:vmi`, so it misses the 90% rule), auditor (1 of 18 runs, `gap:all` seeded, fell back to code after two rejected narratives: T1), narrative (3 of 18 summaries were rejected for adding a number and rewritten by code, all on `fail:all`: T1 and T4). In each failing case the guard did its job and the output was correct; the failure is that the model was not tall enough to be the author. Rung 2 (Sonnet 5.5) was not run: rung 0 clears everywhere and Jim authorized Haiku only.

| Role | Lowest passing rung | Rung 0: code only | Rung 1: Haiku 5.5 | Rung 2: Sonnet 5.5 | First-pass rate at that rung | Cost per successful narrative (USD) | Tokens in / out | Latency (s) |
|---|---|---|---|---|---|---|---|---|
| hmda | 0 (code only) | pass | pass | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| ecoa | 0 (code only) | pass | pass | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| hvcre | 0 (code only) | pass | pass | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| hpml | 0 (code only) | pass | pass | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| trid | 0 (code only) | pass | pass | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| fzd | 0 (code only) | pass | pass | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| ybs | 0 (code only) | pass | pass | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| vmi | 0 (code only) | pass | fail: first-pass rate 78% is below 90% | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| auditor | 0 (code only) | pass | fail: T1×1 | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |
| narrative | 0 (code only) | pass | fail: T1×3, T4×3 | not run: rung 0 cleared the bar (and this run was limited to rung 1) | 100% | 0 (no model request) | 0 / 0 | not timed (code) |

Rung 0 was scored on 27 runs (one per scenario per role). Cost per successful narrative is USD 0 at rung 0 because no model request is made. The cost columns show the lowest passing rung; the Haiku figures are below.

## Haiku 5.5 with `templates: code` (rung 1), 2026-11-07

| Role | Runs | Passing T1-T4 | Verdict | First-pass rate | Retried or fallback | Settled (USD) | Requests | Cost per successful run (USD) | Tokens in / out per successful run | Mean latency (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| hmda | 18 | 18 | pass | 100% | 0 | 0.0900 | 27 | 0.00500 | 34985 / 2094 | 8.5 |
| ecoa | 18 | 18 | pass | 100% | 0 | 0.0438 | 27 | 0.00243 | 14334 / 1555 | 7.1 |
| hvcre | 12 | 12 | pass | 100% | 0 | 0.0186 | 18 | 0.00155 | 7652 / 1293 | 5.7 |
| hpml | 18 | 18 | pass | 100% | 0 | 0.0495 | 27 | 0.00275 | 19135 / 1170 | 5.3 |
| trid | 12 | 12 | pass | 100% | 0 | 0.0323 | 18 | 0.00269 | 17585 / 1382 | 6.1 |
| fzd | 18 | 18 | pass | 100% | 0 | 0.0456 | 27 | 0.00253 | 17383 / 1127 | 5.2 |
| ybs | 12 | 12 | pass | 100% | 0 | 0.0161 | 18 | 0.00134 | 6431 / 1154 | 5.6 |
| vmi | 18 | 18 | fail | 78% | 4 | 0.0449 | 31 | 0.00250 | 15229 / 1494 | 6.6 |
| auditor | 18 | 17 | fail | 94% | 1 | 0.0484 | 29 | 0.00285 | 13551 / 2467 | 9.2 |
| narrative | 18 | 15 | fail | 83% | 3 | 0.0061 | 18 | 0.00041 | 1763 / 391 | 1.8 |

189 runs (scenarios × both tool modes × 3 repetitions per role), 240 requests, **USD 0.39542382 settled** from API usage over 20 reservations (one per role and tool mode, each reserved at its worst case before its first request, largest USD 1.116, then settled). Plan live spend with the two diagnostics: USD 0.4027 of the USD 5 bound. Anthropic ledger after: spent USD 1.02831663, held USD 0.0400224 (an earlier retained diagnostic), remaining USD 18.93. Ledger rows: the 20 reservation and settlement pairs in `usage/anthropic-api-ledger.jsonl` (reservation ids in `runs-anthropic-rung1.jsonl`, `batch_reservation` rows); every request has a `request_start` and `request_outcome` row there. Cost, tokens and latency average both tool modes (model mode makes 2 requests, seeded 1), so they are not like-for-like with the earlier single-mode figures in `plans/response-templates/results.md`, and no saving against `templates: model` is claimed. Cache tokens were 0. Rung 1 under `templates: model` (today's committed setting) was not measured.

Bar amendment, recorded: under `templates: code` the paragraphs are code-written by design, so a paragraph whose source is `code` is not counted as a model rewrite (T4); limits, grounding and the narrative checks (T1-T3) are unchanged. Jim authorized the measurement on 2026-11-07; the change is in `benchmarks/floor_bar.py` with its tests.

## What this does NOT mean (read before changing a setting)

- **Rung 0 is not a setting that exists today.** It means "no model request for the role". `templates: code` in `agents.yaml` only stops the examiner paragraphs being requested from the model; the role's `narrative` object is still the model's. The Haiku table above is that setting, measured.
- The bar passed at rung 0 partly by construction: a rung that asks no model passes T1 and T2 automatically. What it tests there is T3 and T4 (decision parity and the limits on paragraphs and sheet items) and Jim's reads.
- The auditor's model rungs **cannot clear `fail:all` and `gap:all` under `templates: model` whatever the model**: the runtime matches model paragraphs by rule id and the auditor writes `AUD-PRICING` and `AUD-DATES` twice each. That is why only `templates: code` was measured for it; under `templates: code` it failed once on a different cause (a narrative rejected twice). Recorded as a finding, no runtime change (Jim, 2026-11-07).
- Thinking and effort were left as they are (`output_config.effort: low`, thinking unset). Thinking-token billing is unverified (`facts.md`).

## Human reads (T5)

Twelve paragraphs chosen by script from rung 0 (HMDA 4; one each from ECOA, HVCRE, HPML, TRID, FZD, YBS, VMI, auditor), seed `tune-ais-t5-v1`, all code-written. Jim read all twelve on 2026-11-07: **12 of 12 acceptable.** Rule ids and scenarios: HMDA-LAR-04 (sample), HMDA-LAR-12 (sample), HMDA-LAR-ITEMS (fail:hmda), HMDA-COVERAGE (gap:hmda), ECOA-SPOUSE-SIGNATURE (sample), HVCRE-EXCL-SMALL-LOAN (gap:hvcre), HPML-ESCROW (fail:hpml), TRID-LE-3DAY (fail:trid), FZD-APPLICABILITY (fail:fzd), YBS-PERSON-SMALL-PRODUCER (gap:ybs), VMI-REQUEST-MARITAL-STATUS (sample), AUD-AMOUNT (gap:all). Observation, not a rejection: in HPML-ESCROW the Condition repeats the Requirement instead of stating a fact from the record. The paragraphs the model writes under `templates: model` were not read.

## Decision (Jim, 2026-11-07)

`agents.yaml` is **unchanged**: no per-role model and no `templates: code` was applied. Jim chose to plan a separate "no model request" option for the runner, because that is what rung 0 measured and what clears the bar for every role; this plan does not start it. Proposed and not applied: `templates: code` for hmda, ecoa, hvcre, hpml, trid, fzd, ybs (the roles that cleared rung 1), or for all nine tool roles.

## Live diagnostics (one request each, 2026-11-07)

- Haiku 5.5, forced `tool_choice: tool`: accepted, the model called the tool (2430 in / 176 out tokens), ledger reservation `66e5189fa74c435e8ee362f92eaec98d`, settled USD 0.0003641.
- Sonnet 5.5, model mode without a forced choice (`auto` plus an instruction naming the tool): no 400, the model called the tool (2343 in / 164 out), reservation `9560e365a82e4e5dae331cccd65c32dc`, settled USD 0.0069586. Forcing it would have returned a 400 (`facts.md`).

## Not tested

Rung 1 under `templates: model`; rung 2 (Sonnet 5.5) for any role beyond one request; OpenAI and local models (later plans); Opus 5.5, Fable 5.1 and Haiku 4.5 (out of scope); real data; HVCRE and YBS failing cases and the TRID gap case (the fixtures have none); thinking settings; a controlled cost comparison of `templates: code` against `templates: model`.

## Re-run

`python3 -m benchmarks.floor_sweep --dry-run` re-scores rung 0 and prints the table offline (no spend). `python3 -m benchmarks.floor_sweep --live --provider anthropic` adds the two one-request diagnostics (about USD 0.01) and stops with exit 3 instead of spending if any role fails rung 0. The rung 1 measurement above is `python3 -m benchmarks.floor_sweep --live --provider anthropic --climb --rung1 all --templates code --max-rung 1 --out plans/archive/tune-ais/runs-anthropic-rung1.jsonl` (about USD 0.40; needs `ANTHROPIC_API_KEY`). The bar is `benchmarks/floor_bar.py`; the scenarios are `scenarios.md`.
