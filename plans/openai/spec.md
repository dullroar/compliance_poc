# OpenAI narrative provider - specification and execution agreement

Status: approved (by Jim Lehmer, 2026-11-06)

## Goal and exclusions

Add `openai` as a selectable remote inference provider for runtime compliance narratives, using only the OpenAI Responses API. It must coexist with Anthropic and local Ollama, without changing the deterministic evaluators' authority or existing defaults. This work does **not** add DigitalOcean infrastructure, OpenAI hosted agents or built-in tools, a scheduler, deployment automation, new regulatory rules, real-loan API calls, or OpenAI support for the builders.

## Requirements

### R1. OpenAI is a runtime narrator provider

- Basis: documented ([scope boundary](../../docs/design/scope-and-repository-boundary.md), [provider premise](../../docs/design/provider-and-model-selection.md), and [OpenAI Responses overview](https://developers.openai.com/api/reference/responses/overview)); user-directed scope.
- Example: `COMPLIANCE_PROVIDER=openai` and an `OPENAI_API_KEY` create an OpenAI backend; an `agents.yaml` entry can instead select OpenAI only for `auditor` or `narrative` while the other agents retain their own provider/model.
- Acceptance check: the offline backend tests prove `complete`, `complete_with_tool`, and `complete_seeded` work through the same `Backend` interface as the existing providers.

### R2. Deterministic decisions retain exclusive authority

- Basis: documented ([code decides, agents narrate](../../docs/design/code-decides-agents-narrate.md), [narrative guard finding](../../memory/narrate-only-and-grounding-guards.md), and [function-calling guidance](https://developers.openai.com/api/docs/guides/function-calling)); user-directed scope.
- Example: a model-supplied `ybs_evaluate` argument that differs from the canonical `ybs_case` is ignored; OpenAI only receives the evaluator result and returns the existing `NARRATIVE_SCHEMA` prose object.
- Acceptance check: existing decision-authority/grounding tests pass, and new OpenAI tests cover seeded and model tool modes without changing evaluator results.

### R3. Remote use is explicit, bounded, and non-secret

- Basis: documented ([agent contract](../../AGENTS.md), [OpenAI Python reference](https://developers.openai.com/api/reference/python)); user-directed scope.
- Example: `OPENAI_API_KEY` is read only from the environment or untracked `.env`; code and tracked configuration contain no key. Requests use a configurable timeout, disable Responses state storage where supported, use no OpenAI built-in tools, and begin only with synthetic or de-identified inputs.
- Acceptance check: README and config comments document the variables, mixed-provider example, data boundary, and separate API billing; repository secret/context scans pass.

### R4. Failures remain observable and safe

- Basis: documented ([raw and parsed results retained](../../docs/design/raw-and-parsed-results-retained.md)); inferred (the remote transport needs bounded retry behavior, subject to implementation review).
- Example: an OpenAI timeout, rate limit, malformed tool call, or nonconforming narrative cannot alter the decision record; it follows the existing retry/guard/fallback or failed-task behavior and leaves observable error evidence.
- Acceptance check: fake-client tests exercise timeout/API failures and malformed output; the result still retains provider/model/raw-output or parse/guard evidence as the established contracts require.

### R5. The change is reproducibly verified without a live API call

- Basis: documented ([agent contract validation rules](../../AGENTS.md)); user-directed no-infrastructure scope.
- Example: a fake Responses client asserts exact requests, tool-result continuation, structured-output format, and error handling, so CI does not need an API key or network access.
- Acceptance check: the focused test module and the full offline suite pass; `python3 scripts/check_context.py` and `python3 scripts/check_plan.py` pass.

## Constraints and assumptions

- The default provider remains Anthropic; no OpenAI default model is selected until the owner approves a cost/quality target. `COMPLIANCE_MODEL` remains the explicit reproducibility override.
- The OpenAI provider is limited to runtime agent narration, including auditor and final report narration. `builders.build` must continue to accept only its existing providers unless a separate plan expands that scope.
- OpenAI custom function calling may be used only to preserve the existing `tool_mode: model` contract. It must disable parallel tool calls and cannot expose non-evaluator functions or OpenAI built-in tools.
- The preferred initial production-like configuration is `tool_mode: seeded`, because code obtains the decision record before remote narration.
- A live smoke test or any non-synthetic record requires the owner's explicit authority and applicable data-handling review. It is not delegated by this plan.

## Domain challenge

- *Suspicious - explain it:* A provider configured as `openai` with the default `tool_mode: model` could otherwise bypass the safe seeded route. Resolution: implement both modes and document `seeded` as the recommended setting; canonical arguments remain harness-pinned in both.
- *Suspicious - explain it:* Structured Outputs can ensure response shape but cannot prove factual grounding. Resolution: retain the existing narrative fact check, one retry, deterministic fallback, and raw-output retention.
- *Contradicts a confirmed rule:* Letting a model make a compliance determination or adding retrieval/web-search tools would violate the code-decides boundary. Resolution: excluded; only the pre-existing evaluator function is exposed.
- *Suspicious - explain it:* `store: false` is an application state setting, not a complete data-governance determination. Resolution: use it where supported but require separate owner approval before any non-synthetic data is sent.

## Delegated authority

- The executor MAY: edit only the runtime-provider, tool-adapter, CLI validation, dependency, tests, README/config comments, and design documentation named in the steps; add an offline fake-client test module; run the protected local checks.
- The executor MUST NOT: alter evaluator/pack/spec/prompt decisions; make a live OpenAI call; add builders support; change the default provider/model; modify infrastructure; add a key or sample secret; push, publish, or change remotes; weaken, skip, or delete protected checks.

## Acceptance and evidence

- Protected checks (the executor may not edit these without renewed agreement): existing evaluator decision-authority and grounding tests; the new OpenAI fake-client tests; the full offline suite; context and plan validation.
- Combined validation after parallel steps merge: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`.
- Completion evidence is recorded in each step's `evidence:` field. A separately authorized live test may be recorded as supplemental evidence, never substituted for the protected checks.

## Escalate when

The chosen OpenAI model or account policy changes data handling/cost scope; the SDK or Responses API cannot represent the required seeded/function sequence; strict structured output cannot accept the existing narrative schema; a protected check fails; or supporting OpenAI would require changing builders, evaluators, or prompts. Bring back the specific decision and evidence, not a status report.

## Exceptions and retirements

Do not collapse these into "test retired". Record which one applies:

1. Incorrect test - fix or remove the test.
2. Incorrect or outdated documentation - correct the documentation.
3. Requirement withdrawn - record who withdrew it and why.
4. Valid requirement with a tolerated violation - keep the rule; record rationale, decision owner, affected parties, and a review date or trigger (see [exception-record.md](exception-record.md)).
