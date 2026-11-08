---
gist: "Read when: checking which Anthropic model facts (prices, forced tool_choice, thinking and effort defaults) the tune-ais plan rests on, where they were verified and what stayed unverified."
---

# Tune AIs: vendor facts, re-verified 2026-11-07

Every fact in the spec's Goal section was re-read against the vendor documentation on 2026-11-07 (the cached model table the spec used is dated 2026-10-06). Pages were read with the harness web-fetch tool, which returns the start of a long page verbatim and may summarize the rest; the notes below say which. **No fact differs from the spec, so no escalation.** Two items could not be confirmed from the documents and are marked unverified.

## 1. Prices per million tokens, standard Messages API (input / output, USD)

Source: <https://platform.claude.com/docs/en/about-claude/pricing>, "Model pricing" table (verbatim). The page shows no update date.

| Model | Input | Output | Higher tier | Spec said | Estimator `RATES` |
|---|---|---|---|---|---|
| Haiku 5.5 (`claude-haiku-5-5`) | 0.10 | 0.50 | prompts over 100,000 tokens: 0.50 / 2.50 (5 times, whole request, counts cache reads and writes) | 0.10 / 0.50 | 0.10 / 0.50, 5 times above 100,000 input tokens |
| Sonnet 5.5 (`claude-sonnet-5-5`) | 2 | 10 | none | 2 / 10 | 2 / 10 |
| Opus 5.5 (`claude-opus-5-5`) | 4 | 20 | none | 4 / 20 | 4 / 20 |
| Haiku 4.5 (`claude-haiku-4-5-20251001`) | 1 | 5 | none | 1 / 5 | not listed (excluded by the spec) |
| Sonnet 4.6 (`claude-sonnet-4-6`) | 3 | 15 | none | not stated | 3 / 15 |
| Fable 5.1 (`claude-fable-5-1`) | 10 | 50 | none | not stated | not listed (out of scope) |

Multipliers also confirmed on the page for Haiku 5.5: cache write 1.25 times (5 minutes) or 2 times (1 hour), cache read 0.1 times, US-only inference (`inference_geo: "us"`) 1.1 times on every category and on the above-100,000 tier. These are the estimator's assumptions (every input token as a 1-hour cache write, 1.1 times). Haiku 5.5 is the cheapest current Claude model and Haiku 4.5 costs 10 times as much per token, as the spec says. `PRICE_CHECKED` in `scripts/anthropic_cost_estimator.py` is `2026-11-07`, the date of this check.

**Unverified:** how thinking tokens are billed. The pricing page says nothing about thinking. The Messages API reports thinking inside `usage.output_tokens` and thinking shares `max_tokens` with the answer (stated in the comment above `ANTHROPIC_EFFORT` in `compliance_common/tools.py`), so the estimator counts them at the output rate by bounding `output_tokens` per attempt at the `max_tokens` cap, and by an explicit `thinking_tokens` argument for callers that bound them separately. This reading is not confirmed by a page; the live diagnostic's reported usage is the check.

## 2. Forced `tool_choice` (`type: tool` or `any`)

Source: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools>, "Forcing tool use" table (verbatim).

- **Claude Opus 5.5, Sonnet 5.5, Fable 5.1 (and Mythos 5.1): `any` and `tool` return a 400 error**, stated without a condition on thinking. `auto` (the default) and `none` still work. This confirms the spec.
- **Haiku 5.5 is not in the rejecting row.** The same page says models with thinking on by default, "such as Claude Opus 5 and Claude Haiku 5.5, accept it, but a forced call skips thinking". The repository's own live runs already send a forced first call to Haiku 5.5 and pass (tool provenance `model`), so this is also confirmed in practice. The documents do not say whether Haiku 5.5 accepts a forced choice with `thinking: {type: "disabled"}`; that combination is out of scope (this plan leaves thinking unset).
- Manual extended thinking (`thinking: {type: "enabled"}`) is a 400 on all four models; not used here.

Consequence in the code: `compliance_common/tools.py` sends `auto` plus an instruction naming the tool, instead of a forced first call, for exactly these model ids (`claude-sonnet-5-5`, `claude-opus-5-5`, `claude-fable-5-1`, `claude-mythos-5-1`). Every other model, Haiku 5.5 included, keeps today's request byte for byte.

## 3. Thinking and effort defaults

Sources: <https://platform.claude.com/docs/en/about-claude/models/overview> (verbatim table), <https://platform.claude.com/docs/en/build-with-claude/thinking> and <https://platform.claude.com/docs/en/build-with-claude/effort> (verbatim for the first part of each page, summarized after that).

| Model | Thinking, no `thinking` field | Default `effort` | `effort` accepted |
|---|---|---|---|
| Fable 5.1 | adaptive, always on | `high` | `low` `medium` `high` `xhigh` `max` |
| Opus 5.5 | adaptive, always on | `medium` | same |
| Sonnet 5.5 | adaptive (default on) | `high` | same |
| Haiku 5.5 | adaptive (default on) | `medium` | same |

This confirms the spec's premise: the code sends `output_config.effort: low` and leaves `thinking` unset, which is valid on all candidates, and this plan leaves both alone (Jim's decision of 2026-11-07).

## 4. Model ids and Haiku 4.5 status

Model ids as the spec lists them: `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-fable-5-1` (models overview, verbatim). Haiku 4.5 is `claude-haiku-4-5-20251001`: the deprecations page lists it "Active" with retirement "not sooner than October 15, 2026" and the overview lists it under legacy models still available. It is excluded by the spec (older, 10 times the price), not because it is retired.

## What was not checked

- Sonnet 5.5, Opus 5.5 and Haiku 4.5 individual model pages, and the API error page for the forced-tool 400 (the define-tools table was enough).
- Rate limits and account tier (no limit has been named by any error so far; see `plans/archive/parallelize/results.md`).
- Thinking-token billing (above).
