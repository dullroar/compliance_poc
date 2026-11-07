---
gist: "Read when: planning or auditing live synthetic runs of the registry-wide agent-parity behavior against Anthropic and OpenAI."
---

# Live parity runs - specification and execution agreement

Status: complete (approved by Jim Lehmer, 2026-11-06; models claude-haiku-5-5 and gpt-6-luna, separate USD $20 cumulative budgets, synthetic data egress to api.anthropic.com and api.openai.com; verified 2026-11-07, with one tolerated violation recorded in exception-record.md)

See [goal.md](goal.md) for the goal command and execution protocol.

## Goal and exclusions

Show that the improvements delivered by the archived [agent-parity plan](../agent-parity/spec.md) hold against real models. For each provider, run the whole configured registry once, as a live run on synthetic data. One provider uses `claude-haiku-5-5`, the other `gpt-6-luna`. A run drives the production batch and A2A path over in-process ASGI. It has two phases, model-directed then seeded, and covers every domain role from `agents.yaml`, then the auditor, then the narrative role. This is a smoke test with usage accounting. It is not a model comparison, accuracy or compliance certification, rollout, prompt tuning, or replacement for offline checks. It does not use real or de-identified records, other models, tiers, hosted tools, batch APIs, or new defaults.

## Requirements

### R1. Each live run is opt-in, bounded and enforced inside the client

- Basis: documented ([AGENTS.md spending rules](../../../AGENTS.md), [archived smoke-test spec R1](../openai-smoketest/spec.md)); inferred: at most 80 requests and one conservative reservation of at most USD $5 per run.
- Example: with `RUN_LIVE_ANTHROPIC_PARITY` or `RUN_LIVE_OPENAI_PARITY` unset, the live module skips and contacts nothing. When set, the run reserves its worst case first, then a client wrapper refuses any request that would exceed the request cap, the input-byte bound (bytes bound tokens from above), `max_tokens`, or an unexpected model, tier, tool or `store` setting.
- Acceptance check: offline tests in `tests/test_anthropic_live_accounting.py` and `tests/test_openai_live_parity_accounting.py` prove each cap, zero SDK retries, finite timeout, fail-closed behavior and process-restart durability. Live gates: `RUN_LIVE_ANTHROPIC_PARITY=1 python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v` and `RUN_LIVE_OPENAI_PARITY=1 python3 -m unittest discover -s tests -p test_openai_live_parity.py -v`.

### R2. Every registered role keeps deterministic authority through live A2A and batch

- Basis: documented ([agent-parity R2/R3](../agent-parity/spec.md), [code decides, agents narrate](../../../docs/design/code-decides-agents-narrate.md)); inferred: parity must also hold with real models, not only fakes.
- Example: for the synthetic `sample_loan.json` case, each domain role returns the same `decision_id` and classification as direct evaluation, with integers intact via `payload_json` and canonical arguments pinned. The auditor runs after all domains. The narrative role runs after the auditor and emits no domain decision. In the model phase, the model made the tool call, with no harness fallback.
- Acceptance check: the two live gates above assert, for every role in the registry (derived from `agents.yaml`, not hard-coded) and both phases: decision parity, canonical arguments, tool-call provenance, schema validity, ordering, and no leaked decision-owned fields. Each role's narrative source is classified `model`, `model_retry` or `deterministic_fallback`. A run succeeds only if every role is `model` or `model_retry`. A fallback is recorded and reported, never counted as a live narrative.

### R3. Usage and cost are auditable per request, role, phase and run

- Basis: documented ([archived smoke-test R3](../openai-smoketest/spec.md), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [GPT-6 Luna pricing](https://developers.openai.com/api/docs/models/gpt-6-luna)); inferred: a metadata-only run file per provider.
- Example: Anthropic keeps one `reservation` for the whole run and one `settlement` from reported usage in `usage/anthropic-api-ledger.jsonl`. Per-request, per-role and per-phase rows go in `plans/live-parity/runs-anthropic.jsonl`. OpenAI appends to the shared `plans/archive/openai-smoketest/runs.jsonl`, with a role label, plus `plans/live-parity/runs-openai.jsonl`. Cached and reasoning tokens are never double counted.
- Acceptance check: offline tests cover aggregation, retry counting, missing or odd usage (unknown stays null and the reservation is retained), rate selection, settlement not exceeding reservation, and cumulative-cap enforcement across restarts. Existing rows replay to identical totals. Each live run records a complete per-role, per-phase and per-run cost table with cost per successful narrative where the denominator is nonzero.

### R4. Offline validation and the existing smoke test are undisturbed

- Basis: documented ([agent contract](../../../AGENTS.md)).
- Example: the default suite skips every live module; `tests/test_openai_live_smoke.py` still passes its existing assertions and replays the existing ledger rows unchanged.
- Acceptance check: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`, with all `RUN_LIVE_*` variables unset.

## Constraints and assumptions

- Models: `claude-haiku-5-5` (Anthropic default) and `gpt-6-luna` (approved for OpenAI). Account access is unverified. Concurrency is 1 so request order and accounting are deterministic.
- Budgets: separate cumulative USD $20 each, with the Anthropic baseline currently unknown. The baseline must be an owner-confirmed amount (billing dashboard, usage export or Jim's statement) recorded with `anthropic_cost_estimator.py baseline`. The executor never invents or assumes one. A higher budget requires Jim's approval.
- Rates and `PRICE_CHECKED` are fixed to 2026-11-06 in both estimators. On any later date the executor re-verifies rates at the cited URLs, updates the constants and their tests, and escalates if verification is impossible. Haiku above 100k input tokens costs 5x, so the Anthropic input bound must stay at or under 100,000 bytes per request. If the actual outbound payload of any role exceeds that, escalate with the measured sizes; do not guess a smaller token count.
- Only repository synthetic fixtures may leave the machine. Approving this spec authorizes sending `sample_loan.json`-derived cases, repository prompts and the pinned regulation snapshots to `api.anthropic.com` and `api.openai.com`. Inspect every role's complete outbound payload offline before the first request of each provider.
- Worst-case requests per role come from the code (tool-loop turns, one guard retry, harness fallback). The executor derives and records this in step 01 and enforces it. If the total exceeds 80 per run, escalate.

## Domain challenge

- *Suspicious - explain it:* a real model may be rejected by the narrative guard on a role (for example, the largest regulation text). Resolution (inferred): a persistent model-quality fallback is a finding, not a repair target. Prompts, rules and guard behavior are out of scope, so record it per role and escalate. Jim may then accept it as a tolerated violation in [exception-record.md](exception-record.md).
- *Suspicious - explain it:* harness fallback can look like a model tool call. Resolution (inferred): assert provenance (`by`) per role and phase; fallback in model mode fails that role.
- *Suspicious - explain it:* a "free" tokenizer or count endpoint is still an API call. Resolution (inferred): do not use any non-Messages/Responses endpoint without Jim's approval.
- *Contradicts a confirmed rule:* letting a model's arguments alter evaluated facts would break deterministic authority. Resolution: compare with direct evaluation; keep argument pinning.

## Delegated authority

- The executor MAY add live modules, request guards, run-metadata files and focused offline tests; make backward-compatible, tested generalizations of `Ledger` in `tests/test_openai_live_smoke.py` and of `scripts/openai_cost_estimator.py`; run synthetic live runs with the two named models within R1 and the budgets; repair demonstrated shared integration defects in the agent-parity runtime paths (step 06 only); record an owner-confirmed Anthropic baseline using Jim's stated amount; and update README operator notes.
- The executor MUST NOT use real data or other models, tiers, endpoints, hosted tools or batch APIs; change prompts, rules, schemas, thresholds, guard semantics or provider defaults; weaken or delete a protected check or an existing smoke-test assertion; modify or reset a ledger row; raise a budget; print credentials or raw bodies; or push, publish or commit.

## Acceptance and evidence

- Protected checks: both live gates (non-skipped), the offline accounting suites, existing OpenAI fake-client and smoke tests, existing agent-parity tests, full offline suite, and context and plan validation.
- Combined validation: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`, plus both exact live gates in steps 04 and 05.
- Evidence per run: command, interpreter and SDK versions, elapsed time, request counts, API-reported tokens (or explicit unknowns), pricing URL and check date, reservation and settlement, per-role outcomes, tool provenance, guard and retry counts, and fallbacks. Estimated cost is not an invoice; retain reservations when uncertain. `plans/live-parity/results.md` (written in step 06) summarizes both runs side by side without ranking the models.

## Escalate when

Credentials, network or account access are unavailable; the Anthropic baseline is not supplied; rates or the PRICE date cannot be verified; a role's outbound bytes exceed the bound; a worst-case count exceeds 80; the budget or a reservation cannot be funded or safely retained; real data would be needed; a persistent narrative fallback or any protected check fails after in-scope diagnosis; or work would leave delegated paths. Bring the specific decision, not a status report.

## Exceptions and retirements

Distinguish an incorrect test, outdated documentation, a withdrawn requirement and a tolerated violation. Never retire a protected check to get a pass. Record any owner-approved tolerated violation in [exception-record.md](exception-record.md).
