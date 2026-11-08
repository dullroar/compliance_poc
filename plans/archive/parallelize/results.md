---
gist: "Read when: checking the measured speedup of parallel remote agents, why remote_concurrency is 8, or what rate-limit behavior was seen on Anthropic Haiku 5.5."
---

# Parallelize: results

Live run: the existing live-parity gate repeated at remote width 1, 2, 4 and 8 on `claude-haiku-5-5` (synthetic `sample_loan.json`, zero SDK retries, finite timeout of 120 s, production batch path over in-process ASGI, both phases per width, one run each), 2026-11-07, via `RUN_LIVE_ANTHROPIC_PARALLEL=1 python3 -m unittest discover -s tests -p test_anthropic_live_parallel.py -v`. Pricing source `https://platform.claude.com/docs/en/about-claude/pricing`, rechecked 2026-11-07 (Haiku 5.5: USD 0.10 input and 0.50 output per million tokens up to 100,000 prompt tokens and 5 times that above; cache write 2x for one hour, read 0.1x; US-only inference 1.1x; the page states no update date). No OpenAI live run was made.

## Outcome

- Every width ran clean. No rate limit (429) and no other request error, no guard refusal, no failed role, and all 20 role/phase narratives of every run came from the model with no fallback. The ramp therefore did not stop early and no width was backed down.
- Gain on the domain phase (batch start to the last domain role finishing) is far above the 25% threshold at every width above 1: 42% to 77% shorter. The committed `remote_concurrency` is **8**, the highest clean width, by the rule of spec R3.
- Gain flattens above width 4. The domain phase can be no shorter than its slowest role (`hmda`, about 15 s in the model phase and 11 s in the seeded phase), and width 8 reached that floor (14.9 s and 11.1 s). Width 4 to 8 bought 9% in the model phase and 45% in the seeded phase, from one run each.
- Whole-batch time fell less than the domain phase because the auditor (8 to 10 s) and narrative role (about 2 s) cannot overlap with it. One run each is noisy: the width 8 model-phase auditor took 22.0 s against 8 to 10 s in every other run, which is why the width 8 model-phase batch total (38.9 s) is slower than width 4 (28.3 s) although its domain phase is faster.

## Wall time by width (seconds; change against width 1)

Domain phase = from the start of the batch to the last domain role finishing. Whole batch = domain roles, auditor and narrative role.

| Width | Domain, model | Domain, seeded | Whole batch, model | Whole batch, seeded | Auditor, model / seeded |
|---|---|---|---|---|---|
| 1 | 65.9 (0%) | 43.4 (0%) | 77.4 (0%) | 54.7 (0%) | 9.5 / 9.4 |
| 2 | 34.6 (-47.5%) | 25.0 (-42.4%) | 45.8 (-40.8%) | 35.1 (-35.8%) | 9.4 / 8.4 |
| 4 | 16.4 (-75.1%) | 20.2 (-53.5%) | 28.3 (-63.5%) | 30.0 (-45.1%) | 10.0 / 8.1 |
| 8 | 14.9 (-77.3%) | 11.1 (-74.4%) | 38.9 (-49.7%) | 22.5 (-58.9%) | 22.0 / 9.5 |

Both phases together, domain phase: 109.4 s at width 1, 59.6 s (-45.5%) at 2, 36.6 s (-66.5%) at 4, 26.0 s (-76.2%) at 8. Whole batch: 132.1 s, 81.0 s (-38.7%), 58.3 s (-55.8%), 61.4 s (-53.5%). The archived estimate was a 30% fall of the whole batch, from a narrative role that then took 70.8 s; with templates the narrative role takes about 2 s, so the parallel domain phase now accounts for most of the saving.

## Per-role latency (seconds, per call of the role's A2A task)

| Phase | Role | w1 | w2 | w4 | w8 |
|---|---|---|---|---|---|
| model | hmda | 15.9 | 16.2 | 16.4 | 14.9 |
| model | ecoa | 7.9 | 6.3 | 7.2 | 6.8 |
| model | hvcre | 5.5 | 5.5 | 3.6 | 6.3 |
| model | hpml | 8.0 | 8.2 | 6.5 | 6.0 |
| model | trid | 6.1 | 6.8 | 4.4 | 4.9 |
| model | fzd | 5.3 | 2.9 | 3.1 | 3.0 |
| model | ybs | 7.2 | 5.5 | 5.3 | 6.4 |
| model | vmi | 10.0 | 11.6 | 7.5 | 8.0 |
| model | auditor | 9.5 | 9.4 | 10.0 | 22.0 |
| model | narrative | 2.0 | 1.8 | 1.9 | 2.0 |
| seeded | hmda | 10.7 | 11.8 | 14.3 | 11.1 |
| seeded | ecoa | 5.9 | 6.0 | 6.1 | 5.3 |
| seeded | hvcre | 4.2 | 4.4 | 4.3 | 4.1 |
| seeded | hpml | 4.5 | 5.7 | 4.0 | 5.8 |
| seeded | trid | 4.9 | 5.6 | 8.4 | 4.9 |
| seeded | fzd | 2.3 | 1.9 | 1.9 | 2.3 |
| seeded | ybs | 4.6 | 4.8 | 5.4 | 4.8 |
| seeded | vmi | 6.4 | 7.0 | 14.0 | 7.1 |
| seeded | auditor | 9.4 | 8.4 | 8.1 | 9.5 |
| seeded | narrative | 1.9 | 1.7 | 1.8 | 1.9 |

At width 1 the domain roles sum to the domain-phase time (65.9 s, model phase), which is the serial baseline. Per-role times do not rise visibly with width (hmda 15.9, 16.2, 16.4, 14.9 s in the model phase), so no contention showed up on the provider side at eight simultaneous requests.

## Runs, reservations and settlements

Each run reserved the gate's conservative worst case (65 requests of up to 100,000 input bytes and 16,384 output tokens, cache writes at 2x and US premium 1.1x) before the first request, then settled from reported usage. The reservation is above the plan's USD 0.50, as in the live-parity and response-templates runs; USD 0.50 is the cap on settled spend, and the harness refuses to start a run unless spend so far plus 1.5 times the dearest run so far stays within it.

| Width | Run | Requests | Reserved | Settled | Input / output tokens | Cache write / read tokens | Successful narratives |
|---|---|---|---|---|---|---|---|
| 1 | `fb435b58cf134991a8b52b0f5416c2c0` | 29 | USD 2.015728 | USD 0.05026692 | 295137 / 32367 | 0 / 0 | 20 of 20 |
| 2 | `52f4eb04ec714237b2cf434ea86f5a03` | 30 | USD 2.015728 | USD 0.05177029 | 306044 / 32919 | 0 / 0 | 20 of 20 |
| 4 | `e82a49be4ce34e3cb960839916bb9c22` | 30 | USD 2.015728 | USD 0.05205640 | 306225 / 33403 | 0 / 0 | 20 of 20 |
| 8 | `c6ade9cdcdba46deb59f1d202fadc608` | 31 | USD 2.015728 | USD 0.05310008 | 314363 / 33673 | 0 / 0 | 20 of 20 |

- Total settled USD 0.20719369 of the USD 0.50 plan bound. Anthropic ledger after the ramp: spent USD 0.62557011, held USD 0.0400224 (the earlier interrupted diagnostic, still retained), remaining USD 19.33. Rows are in `usage/anthropic-api-ledger.jsonl` (reservation then settlement, four pairs) and per request in `plans/archive/parallelize/runs-anthropic.jsonl` (`request_start` and `request_outcome` for every request, `run_summary` and `width_measurement` per run).
- Request counts differ by one or two (29, 30, 30, 31) because a rejected examiner paragraph costs one retry request; that is model variation, not width.
- Cache tokens were 0 at every width, so no prompt-cache hit was lost to parallel execution (the domain agents use different system prompts, so none were expected).
- Rate-limit events: none. The account tier was not needed because no limit was named.

## What was not measured

- **CPU burst of eight simultaneous evaluator subprocesses.** The live gate runs the evaluators in-process, so it did not show it. Measured separately on 2026-11-08 without any API call: see the section below. The full `--spawn-local` run at width 8 with a real provider was not run.
- OpenAI was not measured in the ramp. One run per width, so differences of a few seconds are within noise. A later single OpenAI check at the committed width is below.
- The 429 path was never reached live. It is covered offline: a role that fails on a rate limit fails alone, the batch summary counts it, and the ramp stops at the width that shows it (`tests/test_batch_concurrency.py`, `tests/test_anthropic_live_parallel.py`).
- Other accounts and tiers may have lower per-minute limits. If an error names a limit, lower `remote_concurrency` in `agents.yaml` or pass `--remote-concurrency N`.

## OpenAI check at the committed width (2026-11-08)

Jim approved one OpenAI live run on 2026-11-08. It used the existing OpenAI live-parity gate (`gpt-6-luna`, synthetic `sample_loan.json`, zero SDK retries, 120 s timeout, standard tier, whole-cycle reservation in the shared ledger) at the committed `remote_concurrency` of 8, through the new opt-in gate `tests/test_openai_live_parallel.py` (`RUN_LIVE_OPENAI_PARALLEL=1`). Pricing page rechecked 2026-11-08: USD 0.10 input, 0.01 cached input, 0.50 output per million tokens, cache write 0.125, 10% regional premium, long-context 2x input and 1.5x output above 272K prompt tokens, Responses API supported; the page states no update date. Rates matched the accounting, so only the pinned check date changed. Run `2fd262243e3e41049ddcc7ffa85c7841`.

- Clean: 0 rate limits (429), 0 other request errors, 0 guard refusals, 0 failed roles, 0 truncated roles, and all 20 role/phase narratives came from the model with no fallback. Usage was reported for every request, so nothing was retained as unknown.
- 30 requests (from the run summary and the ledger; the `width_measurement` row in `runs-openai.jsonl` says 0 because it was written before a counting defect was fixed, and append-only rows are not edited). Reserved USD 3.4584704 (worst case for 56 requests); the reservation was released and the ledger charged USD 0.1283 (cumulative incurred 0.2929 to 0.4211, a conservative budget charge, not a price-based estimate; the gate could not produce one because some usage breakdown fields were not reported).
- Wall time: model phase 42.0 s total (domain 21.8 s, auditor 15.4 s, narrative 4.9 s); seeded phase 32.0 s (domain 13.7 s, auditor 13.1 s, narrative 5.2 s). There is no OpenAI width 1 baseline, so no speedup is claimed for OpenAI.
- Limits of this check: one run at one width; it shows width 8 did not trip this account's limits on this day, not that it is the best width, and it says nothing about other accounts or tiers (the page lists Build tier at 5,000 RPM and 2,000,000 TPM by default).

## Every-regime check on both providers (2026-11-08)

Why: the sample loan produces findings in only four roles (hmda, ecoa, vmi and the auditor), so no live run had asked a model for examiner paragraphs in ybs, hpml, trid, fzd or hvcre. `tests/fixtures/loan_every_regime_fails.json` is the same synthetic loan with one realistic fault per regime (a high APR and missing escrow, late disclosures and fee overruns, a flood-zone loan, a missing producer flag, an ADC loan with the exclusion facts missing), so all eight domain roles and the auditor have findings. One run per provider at the committed width of 8, through the same guarded gates (opt-in `RUN_LIVE_EVERY_REGIME=openai` or `=anthropic`, `tests/test_live_every_regime.py`).

| | OpenAI `gpt-6-luna` (run `db98a0c0b7194154acafd4866f2de158`) | Anthropic `claude-haiku-5-5` (run `a714efb6e4c647b8a2933434fbd63f7e`) |
|---|---|---|
| Roles asked for paragraphs | all 8 domain roles plus the auditor | all 8 domain roles plus the auditor |
| Examiner paragraphs, both phases | 58: 53 model first try, 5 model after one retry, 0 by code | 58: 57 model first try, 1 model after one retry, 0 by code |
| Roles that failed a check | none | `trid` in the model phase (see below) |
| Rate limits / other errors / refusals | 0 / 0 / 0 | 0 / 0 / 0 |
| Requests | 32 | 31 |
| Money | ledger charge USD 0.1478 (reservation USD 3.4584704 released) | settled USD 0.06214153 from usage |

- First-try paragraph failures, by the check that failed (labels recorded by the gate, no text): OpenAI: three HVCRE paragraphs and the ECOA-SPOUSE-SIGNATURE one-off missed the regulation citation or the record's own words; the VMI-FIREWALL paragraph missed both. Anthropic: ECOA-SPOUSE-SIGNATURE missed the outcome word and the record's own words. Every one passed on the single retry. The same VMI paragraph also needed a retry in the earlier OpenAI run, so this is a repeat, not a one-off.
- Anthropic `trid`, model phase: the narrative sentence (not the paragraphs, which were all accepted) was rejected twice and replaced by the code-written narrative. The gate had only the label `other` for it. It can only have been a missing narrative object or a contradiction of the code-decided result; the gate now labels those two separately, so a repeat will say which. The seeded phase of the same role passed. One occurrence, so it is a finding, not a trend.
- A first OpenAI attempt on the fixture (run `1c2f4b63507a4ce6b6941d6201250543`, 15 requests, ledger charge USD 0.0747) was cut short by the gate's own outbound check, which was pinned to the sample loan and refused 10 requests before they left (roles ybs, hpml, trid, fzd, hvcre, both phases). That was a harness limit, not model behavior. The check stays strict by default and now takes an explicit `use_loan` switch for this fixture; the run above is the repeat.
- Limits: one run per provider; paragraph quality is judged only by the code checks (the five parts, the word limit, no invented figure), not by compliance review.

## CPU burst of eight evaluator processes (measured 2026-11-08, no API spend)

The live gates run the evaluators inside one process, so the start-up burst of the real `--spawn-local` path was not seen. Measured separately: the eight domain evaluators (each started as its own `python -m compliance_mcp.<domain>.server` over stdio, the same call the agents make, on the sample loan), serial and then all eight at once, three repeats each after one warm-up, on this laptop (20 logical CPUs, 31 GB memory, idle).

| | Wall time (3 repeats) | Child CPU (3 repeats) | Slowest single call |
|---|---|---|---|
| Serial | 4.38, 4.37, 4.38 s | 4.30, 4.31, 4.32 s | 0.58 to 0.62 s |
| All eight at once | 0.78, 0.76, 0.74 s | 6.00, 5.79, 5.67 s | 0.74 to 0.78 s |

- All eight at once finishes in about 0.76 s instead of 4.4 s. The total CPU rises by about a third (5.8 s against 4.3 s) because the processes compete; on 20 cores the burst is over in under a second.
- On a machine with far fewer cores the same 5.8 CPU-seconds would stretch: roughly 5.8 / cores seconds at best (about 1.5 s on 4 cores). That machine was not tested.
- Not covered: the model calls, the A2A server start-up (once per run, not per call), and the auditor and narrative roles, which run after the domain phase. The full `--spawn-local` run with a real provider at width 8 was not made.

## Known limits accepted as they are (decided 2026-11-08)

- The committed `remote_concurrency` stays 8: the highest width that ran clean on Anthropic (1, 2, 4, 8) and on OpenAI (8, twice). One run per width, so small differences between widths are noise; the gain above width 4 is small because the slowest domain role sets the floor. Another account or tier may have lower limits; `--remote-concurrency N` or `remote_concurrency` in `agents.yaml` lowers it.
- One concurrency stress test failed once and was not reproduced in 180 further runs; the likely cause (a timing assertion of mine) is inferred, not proven. Two Anthropic cap-race tests protect the lock but did not show it was needed, because the GIL hid the race.
- USD 0.0400224 stays held in the Anthropic ledger from an earlier interrupted diagnostic, because the ledger rules retain a reservation when usage is unknown.
- The committed `concurrency: 1` now means local-model agents only; an explicit `--concurrency N` on the command line still caps everything.

