# Agent contract

A2A fan-out orchestrator for Farm Credit ACA compliance agents: regulatory expertise lives in specs/ and prompts/, deterministic evaluators decide, models narrate.

## Load context in this order

1. Read this file.
2. Read the short indexes in full: `README.md`, `docs/README.md`, `memory/README.md`, `scripts/README.md`.
3. Match the task against each index's **Read when** entries and open only matching documents.
4. For a large file, search its headings and read only the relevant ranges.
5. Stop loading when the decision, intended files, constraints and validation method are known.

User instructions take precedence over repository guidance. When sources conflict, prefer: user
instruction, this file, `docs/design/`, the named plan, domain documentation and references,
`memory/`, implementation and tests, historical notes.

## Context ownership

- Universal rules belong here.
- Architectural reasons belong in `docs/design/` (one premise per file).
- Non-obvious findings that cost time to discover belong in `memory/` (one topic per file; edit the existing topic, do not append a rival).
- Execution state belongs in `plans/`; deterministic automation in `scripts/`.
- Every routed Markdown file starts with `gist: "Read when: ..."` front matter. Do not hand-edit the generated section of an index; run `python scripts/build_context_indexes.py`.

Do not duplicate a fact across layers. Correct its canonical source.

## Planned work (spec-driven)

- Work only on a named plan in `plans/<plan>/` (`spec.md` plus `steps/`) or an explicitly identified off-plan task. Copy `plans/TEMPLATE/` to start one.
- Once its spec is approved, proceed through the steps without asking permission for routine work. Failed tests and dead ends inside scope: diagnose, repair, continue. Return to the user only for a new decision: contradictory requirements, scope expansion, or an action outside the spec's delegated authority.
- Acceptance checks named in the spec are protected. Never weaken, skip or delete one to get green; if one cannot pass as written, escalate.
- Parallel steps must have no dependency between them and no overlapping `touches`; if independence is uncertain, serialize. After parallel steps merge, run the spec's combined validation.
- A step is done only with recorded evidence. Report unavailable verification honestly.
- Retiring a rule, correcting documentation, and tolerating a known violation are different outcomes; record which one (see `plans/TEMPLATE/spec.md`).

## Domain content

Regulatory rules live in `specs/` (long-form) and `prompts/` (runtime prompts, version in the header line). Open only the file for the agent you are changing; deterministic evaluators are in `compliance_mcp/<domain>/`.

## Validation

Run the smallest check that proves the change, then `python scripts/check_context.py` for any change to context files.

## Safety

Do not commit credentials, personal data, personal filesystem paths or sensitive record-level examples. Use placeholders and aggregate evidence. Do not push, publish, force-push or add a remote without authorization.

### OpenAI API spending

- Before every OpenAI API call or batch of calls, run `python3 scripts/openai_cost_estimator.py --model <model> --requests <count>` using current verified OpenAI rates and bounded token counts. This preflight is required for every executor, including Claude and Codex; it does not itself reserve funds or authorize a call.
- The cumulative budget for this repository's OpenAI API use is USD $20, including previous calls and unresolved reservations in `plans/archive/openai-smoketest/runs.jsonl`. Never reset, replace, or bypass that ledger. Before submission, persist a conservative reservation covering every possible request, retry, applicable rate and surcharge; record outcomes and usage afterward. Retain the full reservation when usage or billing is unknown. Stop before the bound can exceed $20; a higher budget requires owner approval.
- The existing guarded smoke-test implementation in `tests/test_openai_live_smoke.py` supports only its documented `gpt-6-luna` Responses API configuration and reserves at most six requests per cycle. If another model, endpoint, token limit, service tier, hosted tool, or request pattern is needed, first extend and test the estimator and durable accounting to cover it; do not treat the preflight alone as a spending cap. Verify current rates and their effective date before each cycle. If rates, token bounds, ledger continuity, or conservative reservations cannot be established, stop and escalate.
- These spending rules do not authorize a model, data disclosure, endpoint, or live test by themselves. Respect the active plan and any separate owner approval; never log credentials or raw request/response bodies in the cost ledger.

### Anthropic API spending

- Before every Anthropic API call or batch, use `python3 scripts/anthropic_cost_estimator.py estimate` with the actual model, bounded total input/output tokens per attempt, and the maximum number of calls including SDK, model, and guard retries. Consult `--help` for the required arguments; this preflight makes no API call and does not itself reserve funds.
- Use a separate cumulative USD $20 budget for this repository's Anthropic API use, tracked in `usage/anthropic-api-ledger.jsonl`. Prior spend is initially unknown: reconcile it against billing, a usage export, or an owner-confirmed amount and record the baseline before making a reservation or API call. Never reset or replace the ledger. A higher budget requires owner approval.
- Before submission, use the estimator's `reserve` command to durably hold the full conservative bound; enforce the specified token and attempt limits in the actual caller, including disabling or bounding SDK retries. Settle only with reliable usage or billing evidence. If usage or charges are unknown, retain the full reservation. An estimate or a manual reservation alone cannot enforce limits inside an API client.
- The current estimator covers only its listed models on the first-party, standard Anthropic Messages API with text inputs and no hosted tools, accounting conservatively for cache writes and US data-residency pricing. Verify current rates before use; for any other endpoint, tier, model, modality or hosted tool, extend and test both the estimator and accounting first. Stop if rates, token bounds, budget history or safe enforcement cannot be established. Preserve existing approval and data-handling requirements; never put credentials or raw payloads in the ledger.
