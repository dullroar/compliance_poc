---
gist: "Read when: comparing the live Anthropic and OpenAI registry-wide parity runs, their cost and latency, or the tolerated findings."
---

# Live parity runs - results

Recorded 2026-11-07 against the approved [spec](spec.md). Both runs drove the whole `agents.yaml` registry (8 domain roles, the auditor, then the narrative role) through the production batch and A2A path over in-process ASGI, in the model-directed and seeded phases, on the synthetic `sample_loan.json` case. This is a record of two runs, **not a ranking of the models**: they differ in tokenizer, output length, pricing and runtime defaults, and each ran once on one synthetic case.

## Summary

| | Anthropic `claude-haiku-5-5` | OpenAI `gpt-6-luna` |
|---|---|---|
| Gate | `RUN_LIVE_ANTHROPIC_PARITY=1 ... test_anthropic_live_parity.py` passed, not skipped | `RUN_LIVE_OPENAI_PARITY=1 ... test_openai_live_parity.py` passed, not skipped |
| Run id | `e0b37313116b4a8198e10fe06d14c7bc` | `7ec2e2710b0a40a7940312d6e55e6a85` |
| Requests (cap) | 29 (65) | 29 (56) |
| Elapsed | 232 s | 229 s |
| Input / output tokens | 341448 / 55210 | 219581 / 24394 (of which 6647 reasoning) |
| Cost recorded | USD 0.06792478 (settled from API usage) | USD 0.140894600 conservative budget charge; exact estimate unavailable (the API did not report the cache-write TTL split) |
| Cost per successful narrative | USD 0.003396 | at most USD 0.0070 (conservative bound; exact value not computable) |
| Narratives succeeded | 20 of 20 | 20 of 20 |
| Narrative sources | 20 `model` | 20 `model` |
| Deterministic fallbacks | none | none |
| Guard refusals / SDK retries | 0 / 0 | 0 / 0 |
| Tolerated findings | `narrative` role, both phases: cut off at the 16384 output cap (see below) | none |

An estimated cost is not an invoice. Pricing source and check date: <https://platform.claude.com/docs/en/about-claude/pricing> and <https://developers.openai.com/api/docs/models/gpt-6-luna>, both checked 2026-11-07.

## Per role and phase

Anthropic columns: requests, input / output tokens, cost (USD), latency (s), narrative source. OpenAI columns: the same, with the conservative budget charge as cost.

| Role | Phase | A req | A tokens in / out | A cost | A s | A source | O req | O tokens in / out | O cost | O s | O source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| hmda | model | 2 | 46106 / 2769 | 0.00659461 | 9.7 | model | 2 | 30985 / 1688 | 0.018434350 | 12.0 | model |
| ecoa | model | 2 | 18101 / 1072 | 0.00258071 | 4.9 | model | 2 | 11935 / 633 | 0.007086475 | 7.8 | model |
| hvcre | model | 2 | 8692 / 541 | 0.00125367 | 2.9 | model | 2 | 5672 / 373 | 0.003427325 | 5.0 | model |
| hpml | model | 2 | 25028 / 1714 | 0.00369578 | 7.8 | model | 2 | 16433 / 602 | 0.009534800 | 6.3 | model |
| trid | model | 2 | 22180 / 1382 | 0.00319990 | 5.6 | model | 2 | 14399 / 709 | 0.008504375 | 8.1 | model |
| fzd | model | 2 | 21518 / 731 | 0.00276903 | 3.7 | model | 2 | 14430 / 496 | 0.008345700 | 6.5 | model |
| ybs | model | 2 | 7563 / 1566 | 0.00169323 | 7.5 | model | 2 | 4920 / 489 | 0.003109425 | 5.8 | model |
| vmi | model | 2 | 16770 / 1105 | 0.00245245 | 4.5 | model | 2 | 11124 / 629 | 0.006637125 | 7.0 | model |
| auditor | model | 2 | 7290 / 1540 | 0.00164890 | 6.5 | model | 2 | 4701 / 1169 | 0.003549975 | 11.2 | model |
| narrative | model | 1 | 30704 / 16384 | 0.01238864 | 70.8 | model (tolerated truncation) | 1 | 17443 / 6160 | 0.01467565 | 53.7 | model |
| hmda | seeded | 1 | 25304 / 1382 | 0.00354354 | 5.3 | model | 1 | 17145 / 1083 | 0.010323225 | 7.6 | model |
| ecoa | seeded | 1 | 9884 / 1492 | 0.00190784 | 6.3 | model | 1 | 6631 / 511 | 0.004068625 | 5.5 | model |
| hvcre | seeded | 1 | 4748 / 420 | 0.00075328 | 2.1 | model | 1 | 3190 / 258 | 0.00196735 | 3.1 | model |
| hpml | seeded | 1 | 13636 / 1179 | 0.00214841 | 5.2 | model | 1 | 9080 / 333 | 0.005268725 | 3.6 | model |
| trid | seeded | 1 | 12251 / 776 | 0.00177441 | 3.1 | model | 1 | 8099 / 697 | 0.005029475 | 7.1 | model |
| fzd | seeded | 1 | 11452 / 575 | 0.00157597 | 2.5 | model | 1 | 7779 / 313 | 0.004536675 | 3.5 | model |
| ybs | seeded | 1 | 4641 / 1017 | 0.00106986 | 5.0 | model | 1 | 3123 / 516 | 0.00214335 | 5.1 | model |
| vmi | seeded | 1 | 9285 / 723 | 0.001419 | 3.2 | model | 1 | 6224 / 623 | 0.003937175 | 6.6 | model |
| auditor | seeded | 1 | 14425 / 2458 | 0.00293865 | 9.1 | model | 1 | 8932 / 1282 | 0.00597025 | 11.3 | model |
| narrative | seeded | 1 | 31870 / 16384 | 0.0125169 | 66.0 | model (tolerated truncation) | 1 | 17336 / 5830 | 0.01434455 | 51.8 | model |

Every role passed decision parity, canonical tool arguments, tool provenance (`by: model` in the model phase, `by: seeded` in the seeded phase), schema validity, the no-decision-leak check and registry ordering, on both providers.

## Budgets

| | Spent (recorded) | Held | Remaining of USD 20 |
|---|---|---|---|
| Anthropic (`usage/anthropic-api-ledger.jsonl`, baseline USD 0 owner-confirmed) | USD 0.3679 across 5 live runs and 3 one-request diagnostics | USD 0.0400224 (an interrupted diagnostic whose request status is unknown, retained) | USD 19.59 |
| OpenAI (`plans/archive/openai-smoketest/runs.jsonl`, append-only) | USD 0.2929 including earlier smoke cycles | none | USD 19.71 |

The earlier failed or partial Anthropic runs and their reservations are retained in the ledger and in `runs-anthropic.jsonl`.

## Findings and dispositions

1. **Thinking consumed the output cap (repaired).** At the default effort, Haiku 5.5 spent most of the 8192-token cap thinking and returned the narrative role truncated or with no text. Repaired with Jim's approval: Claude 5-family requests now send `output_config.effort: low` (`compliance_common/tools.py`).
2. **Narrative report longer than the cap (cap raised; remainder tolerated).** Claude's tokenizer produces about 1.7x the tokens of OpenAI's for the same text, and `prompts/narrative.md` asks for a multi-audience report that Haiku writes in full (about 37k characters). The Anthropic cap is now 16384 (`ANTHROPIC_MAX_TOKENS`; OpenAI and Ollama keep 8192), but the report is still cut off in the last audience section. Jim reviewed a sample (coherent, grounded; one miscount in the executive summary) and accepted it as **tolerated violation 1** in [exception-record.md](exception-record.md), review by 2026-12-07 or when the planned audience-template plan lands. The harness still detects and records it, and any other role cut off at `max_tokens` still fails.
3. **Auditor fallback from the contradiction check (repaired).** In earlier runs the auditor fell back to the code-written narrative in 3 of 8 role/phase runs on Anthropic, and needed one retry on OpenAI, because `contradicts_result` rejects a Non-Compliant narrative that says another regime is compliant, which is what a cross-regime summary does. With Jim's approval the check is skipped for the auditor only (`cross_regime`, `agents/runner.py`), regression tests first. The final runs on both providers show no fallbacks or retries.
4. **Shared integration defects:** none found beyond the above. Decision parity, tool provenance and ordering held in every run.

## Notes for readers

- The Anthropic run is on the tokenizer, thinking behaviour and output length of `claude-haiku-5-5` at low effort; the OpenAI run is `gpt-6-luna` at its default reasoning effort. Differences in tokens, cost and latency reflect those settings and one synthetic case.
- The OpenAI exact cost is unavailable because the API did not report the cache-write lifetime split; the budget charge is a conservative upper bound.
- The latest runs were made after the effort, cap and auditor changes, so both reflect the final runtime. Earlier runs are kept in the run files as history.
