---
id: 01-live-foundations
status: done
depends_on: []
touches:
  - tests/live_parity_common.py
  - tests/test_live_parity_common.py
lane: foundation
gate: python3 -m unittest discover -s tests -p test_live_parity_common.py -v && python3 scripts/check_plan.py
requirements: [R2, R3]
evidence: "2026-11-06. Gate `python3 -m unittest discover -s tests -p test_live_parity_common.py -v && python3 scripts/check_plan.py` passed: 17 tests OK; check_plan exit 0. Python 3.12.3 (.venv), anthropic 0.109.1, openai 3.46.0, a2a-sdk 1.2.2, jsonschema 4.26.0. (a) Bounds (tests/live_parity_common.py worst_case_requests): the tool loops in compliance_common/tools.py are `while True`, so the code bounds a role only through the model stopping; the guarded client must therefore enforce a per-role-run cap equal to the most the runner's own paths use. Tool-backed role, model phase = 2 loop turns + 1 harness fallback + 1 guard retry = 4 (both providers); seeded phase = anthropic 2 loop turns + 1 retry = 3, openai 1 + 1 = 2; narrative role = 1 per phase. 8 domains + auditor + narrative x 2 phases: anthropic 36+27+2 = 65, openai 36+18+2 = 56, both <= 80. Offline tests (real SDK loops over an httpx mock transport) show the worst legitimate path reaches the model-phase bound exactly and a model that calls the tool forever is stopped at the cap. (b) Largest first/max outbound request bytes per role (offline recording fake, real SDK serialization, deterministic narratives, no API call): hmda 61771/73217 (largest: openai seeded), ecoa 25265/29849, hvcre 11025/13632, hpml 32584/38455, trid 28736/34861, fzd 30539/34404, ybs 7462/12394, vmi 21830/27086, auditor 5274/35819, narrative 68918/68936; maximum 73217 bytes (anthropic max 72347), under the 100000 bound, no escalation; real model narratives add a few KB, and the guarded client will refuse any request over 100000. (c) usage/anthropic-api-ledger.jsonl holds one row, `baseline_unknown`, so step 04 must block until Jim supplies an owner-confirmed amount; both estimators carry PRICE_CHECKED 2026-11-06 and today is 2026-11-06 (no re-verification needed). Credentials present by name only in .env: ANTHROPIC_API_KEY, OPENAI_API_KEY (values not read). Preflight facts for later steps: anthropic estimate for 65 attempts at 100000 input / 8192 output tokens = USD 1.722864 (< 5 per-run reservation); the OpenAI estimator currently refuses more than 6 requests and prices each at the 1.05M-token context ceiling (0.584 USD), so step 03 must add the per-cycle bounds (56 requests x 100000-token bound ~ USD 3.5)."
---

# Build the provider-neutral registry-run driver and derive the run bounds

Write for an agent with no chat history.

## Change

- `tests/live_parity_common.py`: a driver that, given a `Backend` (real or fake) and a tool mode, runs the production batch path over in-process ASGI: one `build_app` and `ComplianceExecutor` per role from `agents.yaml`, `orchestrator.a2a_client.send`, the real MCP evaluators, then the auditor, then the narrative role. It returns per-role records (decision parity against direct evaluation using the exact `payload_json` facts, canonical arguments, tool-call provenance, narrative source, guard attempts, schema validity, ordering, elapsed time) and a metadata-only summary. It never keeps raw bodies. Reuse the helpers in `tests/test_agent_parity.py` (`role_input`, `parts`, `a2a_task` patterns) by importing them, not by editing that file.
- `tests/test_live_parity_common.py`: offline tests with a fake backend covering every registry role, both phases, parity, fallback classification, ordering and the redaction of raw bodies.
- Derive from the code and record in `evidence:`: (a) per-role worst-case request counts for each provider's tool loop in each phase, with a total that must be at most 80; (b) the UTF-8 byte size of each role's first and largest outbound payload, using an offline recording fake (no API call); (c) the Anthropic ledger state, the estimator `PRICE_CHECKED` date versus today, and credential presence by name only.

## Do not change

Runtime, prompts, agents.yaml, protected tests (including `tests/test_agent_parity.py`), ledgers.

## Dependencies already satisfied

None.

## Completion criteria

The gate passes. Evidence lists the derived bounds and flags any escalation condition (total over 80, any role over 100,000 bytes, stale price date).

## Record

Set `status: done` with the date, command, interpreter, test counts and derived bounds.
