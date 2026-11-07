---
gist: "Read when: planning live synthetic smoke tests for the OpenAI runtime inference provider."
---

# OpenAI inference smoke test - specification and execution agreement

Status: approved (by Jim Lehmer, 2026-11-06)

See [goal.md](goal.md) for the goal command and execution protocol.

## Goal and exclusions

Verify that explicitly selected OpenAI models work with the repository's real Responses API integration and YBS's deterministic MCP and A2A path, using synthetic data. Exercise both seeded and model-directed tool modes. This is a smoke test, not a model comparison, accuracy certification, production rollout, or replacement for offline checks. Do not use real or de-identified loan records, hosted tools, OpenAI builders, new defaults, deployments, or other inference providers.

## Requirements

### R1. The live run is explicit, bounded, and reproducible

- Basis: documented ([provider design](../../docs/design/provider-and-model-selection.md), [archived provider plan](../archive/openai/spec.md)); inferred: at most six Responses requests per model provide a bounded initial smoke test.
- Example: an operator supplies an approved, nonempty list of model IDs, credentials through the environment, and an explicit opt-in; without any of these the live test does not run.
- Acceptance check: the opt-in live test records each selected model, SDK/interpreter versions, mode, elapsed time, per-model and total request counts and outcomes; a request counter prevents more than six Responses requests per model and more than six times the number of selected models in total, including retries and guard retries. Use a finite request timeout and disable SDK retries. Do not record secrets or raw case content.

### R2. Both modes retain deterministic authority through A2A

- Basis: documented ([deterministic authority](../../docs/design/code-decides-agents-narrate.md), [A2A design](../../docs/design/registry-driven-a2a-orchestration.md)); inferred: both existing OpenAI tool modes merit live verification.
- Example: for the same synthetic YBS case, seeded and model-driven A2A tasks for each selected model return the direct evaluator's decision ID and classification; the recorded tool call uses the canonical case, with the appropriate mode.
- Acceptance check: `RUN_LIVE_OPENAI_TESTS=1 python3 -m unittest discover -s tests -p test_openai_live_smoke.py -v` actually contacts OpenAI, verifies both modes and direct-versus-returned decision parity, and proves the model-driven path really called the evaluator rather than only harness fallback. Verify schema/guard results and report retries or fallback explicitly; fallback or malformed output does not count as a successful live narrative.

### R3. The smoke test is opt-in and does not compromise offline validation

- Basis: documented ([agent contract](../../AGENTS.md), [archived provider plan](../archive/openai/spec.md)).
- Example: normal discovery without the opt-in skips all live requests and still runs the existing fake-client and deterministic tests.
- Acceptance check: the default suite, existing OpenAI fake-client tests, context validation, and plan validation pass; live evidence is separately recorded and never represented by a skip.

## Constraints and assumptions

- Owner must approve this spec and identify the model IDs and acceptable total spend before live execution. Model and account availability are unverified; do not infer a model list or spend authority from spec approval.
- Only repository synthetic fixtures may leave the machine; inspect the complete outbound payload, including prompt and regulations, before the first request. Use `store: false` as implemented, without claiming it guarantees broader data handling.
- Preserve evaluator records, model defaults, offline tests and guard behavior. Do not print or persist the API key or raw request/response bodies. API/network unavailability is a blocker, not a pass.

## Domain challenge

- *Suspicious - explain it:* Correct decision parity can coexist with an unusable model response. Resolution (inferred): require valid grounded narrative with no fallback as well as parity, and record guard/retry outcomes separately.
- *Suspicious - explain it:* Harness fallback can look like a successful model tool call. Resolution (inferred): assert the actual model-originated call in model mode and canonical argument pinning; fallback is evidence of failure for that mode.
- *Contradicts a confirmed rule:* Allowing a model's arguments to change the evaluated facts would violate deterministic authority. Resolution: compare with the direct evaluation and retain the existing argument pinning.

## Delegated authority

- Once this spec is approved with model IDs and a spend bound, the executor MAY add an opt-in live test and focused offline tests, edit directly related runtime code and documentation if needed to meet the existing provider contract, and make at most six Responses requests per approved model and at most six times the number of approved models overall, using synthetic data and within the approved spend bound. One execution attempt is authorized; a new run after exhausted budget needs a new approval.
- The executor MUST NOT use real data or unapproved models; change evaluator rules, decisions, defaults, or protected checks; print credentials or raw sensitive payloads; add hosted tools; push, publish, or commit.

## Acceptance and evidence

- Protected checks: both real A2A modes, canonical argument and direct decision parity, valid grounded non-fallback narration, no live requests without opt-in, existing OpenAI fake-client tests, full offline suite, context and plan validation.
- Combined validation: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`; additionally run the exact opt-in live gate in step 02 with the approved model and credentials present.
- Record dates, commands, interpreter and SDK versions, selected models, bounded per-model and total request counts, elapsed time, outcomes and any fallback or errors in step evidence. Keep secrets and raw payloads out of evidence.

## Escalate when

Approval, model IDs, spend bound, credentials or network access are unavailable; a model's six-request bound or the total bound is reached before all required modes pass; the account/model cannot support the required API contract; real data would be needed; a protected check cannot pass; or scope must expand. Record the failure and requests consumed; do not mark completion.

## Exceptions and retirements

Distinguish incorrect tests, outdated documentation, withdrawn requirements and tolerated violations. Never retire or weaken a protected check to obtain a pass; record any approved tolerated violation in [exception-record.md](exception-record.md).
