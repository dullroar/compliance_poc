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

- Total settled USD 0.20719369 of the USD 0.50 plan bound. Anthropic ledger after the ramp: spent USD 0.62557011, held USD 0.0400224 (the earlier interrupted diagnostic, still retained), remaining USD 19.33. Rows are in `usage/anthropic-api-ledger.jsonl` (reservation then settlement, four pairs) and per request in `plans/parallelize/runs-anthropic.jsonl` (`request_start` and `request_outcome` for every request, `run_summary` and `width_measurement` per run).
- Request counts differ by one or two (29, 30, 30, 31) because a rejected examiner paragraph costs one retry request; that is model variation, not width.
- Cache tokens were 0 at every width, so no prompt-cache hit was lost to parallel execution (the domain agents use different system prompts, so none were expected).
- Rate-limit events: none. The account tier was not needed because no limit was named.

## What was not measured

- **CPU burst of eight simultaneous evaluator subprocesses.** The live gate runs the evaluators in-process (`target_for` in `tests/live_parity_common.py`), not as MCP stdio subprocesses, so child CPU read 0.0 s and the process itself used 0.4 to 0.5 s of CPU per phase at every width. The subprocess start-up burst the spec mentions belongs to the `orchestrator.cli batch --spawn-local` path and was not measured; the first such run at width 8 on this laptop should be watched.
- OpenAI was not measured (needs Jim's separate approval). One run per width, so differences of a few seconds are within noise.
- The 429 path was never reached live. It is covered offline: a role that fails on a rate limit fails alone, the batch summary counts it, and the ramp stops at the width that shows it (`tests/test_batch_concurrency.py`, `tests/test_anthropic_live_parallel.py`).
- Other accounts and tiers may have lower per-minute limits. If an error names a limit, lower `remote_concurrency` in `agents.yaml` or pass `--remote-concurrency N`.
