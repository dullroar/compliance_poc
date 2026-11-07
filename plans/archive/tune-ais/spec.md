---
gist: "Read when: planning or auditing the cheapest-adequate-model spike or the dated 'you must be this tall' baseline for Anthropic models."
---

# Tune AIs - specification and execution agreement

Status: complete (approved by Jim Lehmer, 2026-11-07; executed and archived 2026-11-07; result in floor.md). Decided by Jim 2026-11-07: the thinking-off work is dropped; thinking and effort settings stay as they are today. Rules marked inferred still need confirmation.

See [goal.md](goal.md) for the goal command.

## Goal and exclusions

Code now decides and templates now shape the text, so a model only phrases. Find the lowest-compute setting that still passes a fixed quality bar, and record it as a dated floor ("you must be this tall to ride") for Anthropic. The floor is a measured, re-runnable baseline. It will go out of date; the harness exists so it can be re-run.

Facts the plan rests on (cached model table of 2026-10-06 and archived runs; step 01 re-verifies them):

- Today the code sends `output_config.effort: low` to Claude 5-family models and leaves `thinking` unset ([`compliance_common/tools.py`](../../../compliance_common/tools.py)). This plan leaves both as they are.
- Sonnet 5.5, Opus 5.5 and Fable 5.1 reject forced `tool_choice` of type `tool` or `any` (400). The runtime forces the first Anthropic tool call, so those models cannot run model mode without a change. Haiku 5.5 is not listed as rejecting it; step 01 verifies.
- Per million tokens, input/output: Haiku 5.5 USD 0.10/0.50, Sonnet 5.5 2/10, Opus 5.5 4/20, Haiku 4.5 1/5. Haiku 5.5 is already the cheapest current Claude model, and Haiku 4.5 costs 10 times as much. So the floor cannot be found by going to a cheaper Claude model. It is found by checking whether Haiku 5.5 is tall enough, whether any role needs more, and whether code alone is enough for some roles.

This work does NOT: change a rule, pack, `decision_id` or compliance result; choose or test local models (a later plan); change thinking or effort settings for any provider; run any OpenAI live call; change prompts' regulatory content; tune prompts to pass the bar; or apply a new default model or per-role setting without Jim's decision (step 04).

## Requirements

### R1. Candidate models can run the same path and be priced before use

- Basis: documented ([AGENTS.md Anthropic spending](../../../AGENTS.md): only listed models, first-party standard Messages API; extend and test the estimator and accounting first); the estimator lists `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-sonnet-4-6`.
- Rule: first re-verify the model facts above against vendor documentation and record sources and date in `plans/archive/tune-ais/facts.md`. Then model mode on Sonnet 5.5 works without forced `tool_choice` (use `auto` plus an instruction naming the tool; the harness already covers a model that does not call it and records `by: harness`). Haiku 5.5 keeps forced choice if the API accepts it. The live guard allow-list admits the candidate model ids and nothing else new. The estimator counts thinking tokens at the output rate.
- Example: a Sonnet 5.5 role run completes in model mode with tool provenance `model` or `harness`, never a 400. Request bodies for Haiku 5.5 are byte-for-byte unchanged from today.
- Acceptance check: offline tests for request shape per model, guard refusals of everything else, and estimator rates per candidate; the first live call of each new model is a one-request diagnostic inside the reservation.

### R2. The bar is written down before any model is run

- Basis: inferred. Jim confirms it before step 03.
- Rule (inferred): for a given role, setting, scenario and tool mode, a run passes only if all hold. T1: the narrative source is `model` or `model_retry`, never a code fallback. T2: no output stopped at `max_tokens`. T3: decision id and classification equal direct evaluation (a sanity check; code owns it). T4: every examiner paragraph and loan-officer item passes the limits of plan `response-templates` after at most the one retry. A setting clears the bar for a role when, over 3 repetitions of each scenario in both tool modes, T1-T4 hold in all runs and the first-pass (`model`, no retry) rate is at least 90%. T5: Jim reads a fixed sample of 12 paragraphs (HMDA 4, others 1 or 2 each, chosen by script from the cheapest passing setting) and marks each acceptable or not; all 12 must be acceptable.
- Scenarios (inferred): `sample_loan.json` plus, for each regime, one failing and one information-gap case drawn from `tests/fixtures/*/scenarios.json`, chosen by script and recorded.
- Acceptance check: `benchmarks/floor_bar.py` encodes T1-T4 with its own offline tests, including cases that must fail; the bar file is committed before the first live run, and a later change to it is a recorded decision.

### R3. The ladder is climbed only as far as needed, and a no-model rung is measured

- Basis: inferred.
- Rungs, cheapest first: 0 code only (`templates: code`, deterministic narrative, no model request for that role); 1 Haiku 5.5 at today's setting; 2 Sonnet 5.5 at effort low, thinking unset. A role stops at the first rung that clears the bar. Rung 2 is run only for roles that fail rungs 0-1, to learn whether any Claude model clears it. Opus and Fable are out of scope. Haiku 4.5 is excluded: older, 10 times the price.
- Acceptance check: the run file records, per role, each rung tried and its pass or fail on T1-T4, so a skipped rung is visible and justified.

### R4. The floor report is dated, costed and re-runnable

- Basis: inferred.
- Rule: `plans/archive/tune-ais/floor.md` states, per role: the lowest passing rung, cost per successful narrative at that rung (API usage, not guessed), tokens, latency, and the date and pricing source. It states what was not tested. `memory/` gets one short topic pointing to the report and the command to re-run it. The command re-runs the whole sweep from the committed bar and scenarios and prints a table comparable with the committed report.
- Acceptance check: the run command works offline with fakes (`--dry-run`) and the report cites the ledger rows for its live evidence.

### R5. Spend stays inside a stated bound

- Basis: documented ([AGENTS.md Anthropic spending](../../../AGENTS.md)); inferred: bound.
- Rule: total live spend for this plan at most USD 5 of the existing USD 20 Anthropic budget (remaining about USD 19.59 at the last record); each run reserved first at its worst case, at most USD 1.50 per run; zero SDK retries; request and byte caps from the live gate. For scale: one full Haiku registry run (both phases) cost USD 0.068 in the archive; Sonnet 5.5 is 20 times the per-token price, so it is run per role, not per registry.
- Acceptance check: the ledger shows reservations before calls, settlements from usage, and the total under the bound.

### R6. Existing behavior and validation are undisturbed

- Basis: documented ([agent contract](../../../AGENTS.md)).
- Acceptance check: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`, all `RUN_LIVE_*` variables unset.

## Constraints and assumptions

- Depends on plan `response-templates` (T4 and the `templates` option) and should follow `parallelize` (the sweep is faster, and the guards are thread-safe). Do not start before both are complete; both change files this plan reads. When the sweep runs, it uses the width that `parallelize` committed.
- Model facts above are from a cache dated 2026-10-06 and from the archived runs. Step 01 re-verifies each and records the date. If a fact has changed, update the spec before continuing.
- One synthetic loan family only. The floor is a floor for this workload and these scenarios, not for production data. Say so in the report.
- Quality here is rule-based plus 12 human reads. It is not a compliance certification.

## Domain challenge

- *Suspicious - explain it:* a cheaper rung that "passes" only because the retry rescues it. Resolution: the 90% first-pass requirement; retries are counted and reported.
- *Suspicious - explain it:* rung 0 (no model) may be good enough for some roles, which would make a model call pure cost for them. Resolution: report it plainly; whether to drop the model for a role is Jim's decision (step 04).
- *Suspicious - explain it:* the Haiku 5.5 price is 5 times higher above 100,000 input tokens. Resolution: keep the input bound of the live gate at or under 100,000 bytes per request and report any role near it.
- *Contradicts a confirmed rule:* tuning prompts or rules until a cheaper model passes. Out of scope; a failing role is a finding.

## Delegated authority

- The executor MAY: change `compliance_common/tools.py` and `agents/backends.py` only for the forced-tool-choice change in R1; extend `scripts/anthropic_cost_estimator.py` and the live guard and accounting tests for candidate models; add `benchmarks/floor_bar.py`, a sweep script and offline tests; run the bounded live sweep on Anthropic with synthetic data (R5); write `facts.md`, `floor.md`, the run file, a `memory/` topic and README notes; run single-request diagnostics for each new model inside the reservation.
- The executor MUST NOT: change rules, packs, prompts' regulatory content, output caps used by the live gates, thinking or effort settings, or provider defaults; apply a per-role model or `templates: code` to the committed `agents.yaml` (Jim decides in step 04); run OpenAI live calls; use real data; weaken or delete a protected check; exceed R5; push, publish or commit.

## Acceptance and evidence

- Protected checks: R1, R2, R4-R6 suites, the live accounting suites, the bar's own tests, context and plan validation.
- Combined validation: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`.
- Evidence per step in `evidence:`; the floor report is the main artifact.

## Escalate when

A vendor fact differs from this spec; no rung clears the bar for a role; the bound would be exceeded; Jim's T5 reads reject the cheapest passing rung; or applying a floor to `agents.yaml` is next. Bring the specific decision.

## Exceptions and retirements

None expected. A role that clears no rung is a recorded finding for Jim, not a lowered bar.
