---
gist: "Read when: planning live synthetic smoke tests for the OpenAI runtime inference provider."
---

# OpenAI inference smoke test - specification and execution agreement

Status: approved (by Jim Lehmer, 2026-11-06; model, budget, usage tracking and repeat cycles approved 2026-11-06)

See [goal.md](goal.md) for the goal command and execution protocol.

## Goal and exclusions

Verify that the selected OpenAI model works with the repository's real Responses API integration and YBS's deterministic MCP and A2A path, using synthetic data. Exercise both seeded and model-directed tool modes. This is a smoke test, not a model comparison, accuracy certification, production rollout, or replacement for offline checks. Do not use real or de-identified loan records, hosted tools, OpenAI builders, new defaults, deployments, or other inference providers.

## Requirements

### R1. The live run is explicit, bounded, and reproducible

- Basis: documented ([provider design](../../docs/design/provider-and-model-selection.md), [archived provider plan](../archive/openai/spec.md)); inferred: at most six Responses requests per cycle provide a bounded smoke test.
- Example: the approved model is `gpt-6-luna`; an operator supplies credentials through the environment and an explicit opt-in; without those prerequisites the live test does not run.
- Acceptance check: the opt-in live test records the model, SDK/interpreter versions, mode, elapsed time, request counts and outcomes; a request counter prevents more than six Responses requests per cycle, including retries and guard retries. The cumulative conservative spending bound across all cycles cannot exceed $20. Use a finite request timeout and disable SDK retries. Do not record secrets or raw case content.

### R2. Both modes retain deterministic authority through A2A

- Basis: documented ([deterministic authority](../../docs/design/code-decides-agents-narrate.md), [A2A design](../../docs/design/registry-driven-a2a-orchestration.md)); inferred: both existing OpenAI tool modes merit live verification.
- Example: for the same synthetic YBS case, seeded and model-driven A2A tasks for `gpt-6-luna` return the direct evaluator's decision ID and classification; the recorded tool call uses the canonical case, with the appropriate mode.
- Acceptance check: `RUN_LIVE_OPENAI_TESTS=1 python3 -m unittest discover -s tests -p test_openai_live_smoke.py -v` actually contacts OpenAI, verifies both modes and direct-versus-returned decision parity, and proves the model-driven path really called the evaluator rather than only harness fallback. Verify schema/guard results and report retries or fallback explicitly; fallback or malformed output does not count as a successful live narrative.

### R3. Each test run has auditable usage and estimated cost

- Basis: documented ([Responses API token accounting](https://developers.openai.com/api/docs/guides/token-counting), [GPT-6 Luna pricing](https://developers.openai.com/api/docs/models/gpt-6-luna)); inferred: a persistent run ledger is needed to compare tests and enforce the cumulative budget.
- Example: a seeded run and a model-directed run each record every request, their API-reported input, cached-input, output, reasoning and total tokens when available, estimated USD cost, outcome and elapsed time; the ledger also totals the complete cycle and cumulative plan expenditure.
- Acceptance check: focused offline tests prove per-request and per-mode aggregation, retry accounting, cache and reasoning breakdown without double counting, rate selection and arithmetic, missing usage and timeout handling, durable reservation and recovery, and cumulative budget enforcement across process restarts. The live gate records usage for both modes; absent API usage is explicitly unknown, never zero or a fabricated price.

### R4. The smoke test is opt-in and does not compromise offline validation

- Basis: documented ([agent contract](../../AGENTS.md), [archived provider plan](../archive/openai/spec.md)).
- Example: normal discovery without the opt-in skips all live requests and still runs the existing fake-client and deterministic tests.
- Acceptance check: the default suite, existing OpenAI fake-client tests, context validation, and plan validation pass; live evidence is separately recorded and never represented by a skip.

## Constraints and assumptions

- The owner approved `gpt-6-luna` and a maximum total testing budget of USD $20 on 2026-11-06. Account access is unverified. Each cycle is one execution of both tool modes with at most six Responses requests. Repeat cycles as needed to diagnose and verify in-scope issues, within the cumulative $20 budget; do not add models without approval. Before each cycle and each request, reserve a conservative upper bound based on current applicable rates and bounded input/output tokens, including relevant surcharges and all retries. Persist reservations before submission; if usage is unknown, retain its full bound against the budget until reconciled. Do not launch if cumulative incurred and reserved costs could exceed $20. A count of requests alone is not a spending cap.
- Only repository synthetic fixtures may leave the machine; inspect the complete outbound payload, including prompt and regulations, before the first request. Use `store: false` as implemented, without claiming it guarantees broader data handling.
- Preserve evaluator records, model defaults, offline tests and guard behavior. Do not print or persist the API key or raw request/response bodies. API/network unavailability is a blocker, not a pass.

## Domain challenge

- *Suspicious - explain it:* Correct decision parity can coexist with an unusable model response. Resolution (inferred): require valid grounded narrative with no fallback as well as parity, and record guard/retry outcomes separately.
- *Suspicious - explain it:* Harness fallback can look like a successful model tool call. Resolution (inferred): assert the actual model-originated call in model mode and canonical argument pinning; fallback is evidence of failure for that mode.
- *Contradicts a confirmed rule:* Allowing a model's arguments to change the evaluated facts would violate deterministic authority. Resolution: compare with the direct evaluation and retain the existing argument pinning.

## Delegated authority

- The executor MAY add an opt-in live test, usage ledger and focused offline tests; edit directly related runtime code and documentation if needed to meet the existing provider contract; and run repeated synthetic `gpt-6-luna` cycles as needed within six Responses requests per cycle and the cumulative $20 bound. A new budget or model requires owner approval.
- The executor MUST NOT use real data or unapproved models; change evaluator rules, decisions, defaults, or protected checks; print credentials or raw sensitive payloads; add hosted tools; push, publish, or commit.

## Acceptance and evidence

- Protected checks: both real A2A modes, canonical argument and direct decision parity, valid grounded non-fallback narration, per-run usage and cost accounting, no live requests without opt-in, existing OpenAI fake-client tests, full offline suite, context and plan validation.
- Combined validation: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`; additionally run the exact opt-in live gate in step 02 with the approved model and credentials present.
- Persist an append-only, machine-readable ledger at `plans/openai-smoketest/runs.jsonl`, using a unique cycle ID, mode and request sequence. Record reservation before each request and outcome/usage after it, even on failure or interruption. Record model, timestamp, service tier, pricing URL, rate values and effective/check date, request outcome, input, cached-input and cache-write token details when reported, output, reasoning and total tokens, and estimated USD cost; unknown fields must be null with an explanation. Reasoning tokens are included in output, and cached tokens in input: never add them twice. Apply actual documented rates to the appropriate categories when known; where price details are missing, label the estimate unavailable or conservative rather than inventing a charge.
- Record per-mode and per-cycle totals and cumulative incurred plus reserved costs, interpreter/SDK versions, exact command, elapsed time, outcomes, guard/retry status, and successful narrative count. Provide cost per successful narrative and per completed cycle only when complete data and a nonzero denominator permit. Estimated cost is not an invoice; reconcile uncertain charges against account billing where available, retaining reservations otherwise. Keep credentials, prompts, raw output and case content out of the ledger and evidence.

## Escalate when

Credentials or network access are unavailable; the cumulative budget or conservative reservation is exhausted; missing usage cannot be reconciled or safely reserved; current rates or token bounds cannot be established; the account/model cannot support the required API contract; real data would be needed; a protected check cannot pass after in-scope diagnosis; or scope must expand. A cycle that exhausts its six-request cap fails, but another cycle may proceed if it can be safely funded. Record failed cycles, requests and reserved cost; do not mark completion.

## Exceptions and retirements

Distinguish incorrect tests, outdated documentation, withdrawn requirements and tolerated violations. Never retire or weaken a protected check to obtain a pass; record any approved tolerated violation in [exception-record.md](exception-record.md).
