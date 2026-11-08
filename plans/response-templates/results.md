---
gist: "Read when: checking what the response-templates plan changed in cost, tokens, latency and narrative length, or whether the narrative truncation tolerance was closed."
---

# Response templates: results

Live run: one Anthropic run of the existing gate (`claude-haiku-5-5`, synthetic data, zero SDK retries, finite timeout), 2026-11-07, run `04cf37c16a8a43649ad96ebc96efd55d`. Pricing source `https://platform.claude.com/docs/en/about-claude/pricing`, rechecked 2026-11-07 (Haiku 5.5: USD 0.10 input and 0.50 output per million tokens up to 100,000 prompt tokens, 1-hour cache write 2x, US-only inference 1.1x; the page states no update date). No OpenAI live run was made.

## Outcome

- The gate passed non-skipped: 20 role/phase runs, every `narrative_source` `model`, no fallback, no failed check, and the `narrative` role passed `not_truncated` with no tolerance (`TOLERATED_TRUNCATION` is gone).
- 29 requests (the minimum for the gate: 19 in the model phase, 10 in the seeded phase), so no role needed a retry. A rejected examiner paragraph would have cost a retry request, so every examiner paragraph passed its checks on the first reply (source `model`); the gate does not record paragraph sources, so this is inferred from the request count, not read from a field.
- Reservation USD 2.015728 (the gate's worst case, approved by Jim as above the plan's USD 0.50 bound, with USD 0.50 as the cap on settled spend). Settled from API usage at USD 0.05044523, which is under USD 0.50. Anthropic ledger after the run: spent USD 0.41837642, held USD 0.0400224 (an earlier interrupted diagnostic, retained), remaining USD 19.54.

## Narrative role, before and after

| | Before (archived run) | After |
|---|---|---|
| model phase output tokens | 16384 (the cap; report cut off mid-sentence) | 316 |
| seeded phase output tokens | 16384 (the cap; cut off) | 411 |
| model phase cost | USD 0.01238864 | USD 0.00033231 |
| seeded phase cost | USD 0.0125169 | USD 0.00038456 |
| latency (model, seeded) | 70.8 s, 66.0 s | 1.7 s, 2.0 s |
| input tokens (model, seeded) | 30704, 31870 | 1441, 1441 |

The output is about 2% of the 16384-token cap. The report itself is assembled by code, so its length no longer depends on the model.

## Every role: requests / input tokens / output tokens / cost (USD) / seconds

Before = archived run in `plans/archive/live-parity/results.md` (earlier prompts, no examiner paragraphs). After = this run (contract with `examiner_paragraphs`, drafts in the tool result).

| Role | Phase | Before | After |
|---|---|---|---|
| hmda | model | 2 / 46106 / 2769 / 0.00659461 / 9.7 | 2 / 48319 / 5181 / 0.00816464 / 17.3 |
| ecoa | model | 2 / 18101 / 1072 / 0.00258071 / 4.9 | 2 / 18908 / 1799 / 0.00306933 / 7.7 |
| hvcre | model | 2 / 8692 / 541 / 0.00125367 / 2.9 | 2 / 9259 / 972 / 0.00155309 / 4.9 |
| hpml | model | 2 / 25028 / 1714 / 0.00369578 / 7.8 | 2 / 25571 / 1529 / 0.00365376 / 7.4 |
| trid | model | 2 / 22180 / 1382 / 0.00319990 / 5.6 | 2 / 22747 / 1642 / 0.00340527 / 6.8 |
| fzd | model | 2 / 21518 / 731 / 0.00276903 / 3.7 | 2 / 22085 / 582 / 0.00274945 / 2.9 |
| ybs | model | 2 / 7563 / 1566 / 0.00169323 / 7.5 | 2 / 8106 / 1471 / 0.00170071 / 6.9 |
| vmi | model | 2 / 16770 / 1105 / 0.00245245 / 4.5 | 2 / 17794 / 2048 / 0.00308374 / 7.9 |
| auditor | model | 2 / 7290 / 1540 / 0.00164890 / 6.5 | 2 / 8362 / 2096 / 0.00207262 / 8.7 |
| narrative | model | 1 / 30704 / 16384 / 0.01238864 / 70.8 | 1 / 1441 / 316 / 0.00033231 / 1.7 |
| hmda | seeded | 1 / 25304 / 1382 / 0.00354354 / 5.3 | 1 / 27241 / 3599 / 0.00497596 / 11.9 |
| ecoa | seeded | 1 / 9884 / 1492 / 0.00190784 / 6.3 | 1 / 10415 / 1634 / 0.00204435 / 6.2 |
| hvcre | seeded | 1 / 4748 / 420 / 0.00075328 / 2.1 | 1 / 5039 / 715 / 0.00094754 / 3.3 |
| hpml | seeded | 1 / 13636 / 1179 / 0.00214841 / 5.2 | 1 / 13927 / 1739 / 0.00248842 / 8.3 |
| trid | seeded | 1 / 12251 / 776 / 0.00177441 / 3.1 | 1 / 12542 / 1119 / 0.00199507 / 5.0 |
| fzd | seeded | 1 / 11452 / 575 / 0.00157597 / 2.5 | 1 / 11743 / 414 / 0.00151943 / 1.9 |
| ybs | seeded | 1 / 4641 / 1017 / 0.00106986 / 5.0 | 1 / 4932 / 1166 / 0.00118382 / 5.4 |
| vmi | seeded | 1 / 9285 / 723 / 0.001419 / 3.2 | 1 / 10033 / 1704 / 0.00204083 / 6.3 |
| auditor | seeded | 1 / 14425 / 2458 / 0.00293865 / 9.1 | 1 / 15218 / 2557 / 0.00308033 / 9.5 |
| narrative | seeded | 1 / 31870 / 16384 / 0.0125169 / 66.0 | 1 / 1441 / 411 / 0.00038456 / 2.0 |

Per run: 29 requests, 295123 input and 32694 output tokens, USD 0.05044523.

## Word counts and sources of the templates

Word counts per regime on the fixture sweep (code-written paragraphs; limit in brackets) are in step 03's evidence in `plans/response-templates/steps/03-examiner-finding.md`: ybs 49-64 (70), hpml 61-68 (90), trid 70-77 (100), hmda 53-106 (130), ecoa 54-84 (100), vmi 63-90 (100), fzd 63-82 (90), hvcre 54-80 (90), auditor 50-76 (110). No role fell back to code paragraphs in the live run (see Outcome for how that is known).

## Caveats

- One synthetic case and one run. Most roles have few or no findings on `sample_loan.json` (hmda 7, ecoa 1, vmi 2, auditor 2, others 0), so the live run exercised paragraph rephrasing on four roles only.
- Anthropic has no schema-constrained output here; the paragraphs relied on the prompt contract and the checks, and they passed.
- Input tokens rose for some roles (the contract grew and the tool result carries drafts). Totals differ from the earlier run mainly because of the narrative role.
- OpenAI was not run live in this plan's run. A later OpenAI run on 2026-11-08 (run `2fd262243e3e41049ddcc7ffa85c7841`, see `plans/parallelize/results.md`) had every role pass `not_truncated` with all 20 narratives from the model and the narrative role taking 4.9 s and 5.2 s, so "no truncation on both providers" now holds on one OpenAI run. The same day, one run per provider on a loan with findings in every regime (see `plans/parallelize/results.md`) asked each model for examiner paragraphs in all eight regimes and the auditor: 58 paragraphs on each provider, none written by code, a few accepted only after the one retry.

## Known limits left as they are (decided 2026-11-08)

- `HMDA-LAR-FIELDS` has an explanation entry in `compliance_mcp/auditor/rules.py`, but no HMDA check emits that rule id (the evaluator emits `HMDA-LAR-01` to `HMDA-LAR-38`). It is harmless; `tests/test_response_catalog.py` asserts it stays unemitted. Removing it would edit the auditor rules, outside this plan.
- When a regime's case section is missing from the loan file, the loan-officer sheet gives one generic "record unavailable, refer to compliance" referral, because the catalog has no entry for those input names. The result is safe (never a customer request) but not regime-specific.
- The draft wording and the HMDA section grouping await compliance review: see `compliance-review-packet.md`.

