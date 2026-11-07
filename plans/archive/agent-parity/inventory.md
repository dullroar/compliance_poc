---
gist: "Read when: checking which registered agent roles have verified YBS-baseline runtime, MCP, A2A and orchestration coverage, or which gaps remain."
---

# Agent parity inventory

Derived 2026-11-06 from `agents.yaml`, `prompts/*.md` (via `agent_prompts.AGENTS`), the runtime and the existing tests. Re-derive the role set from the registry rather than trusting this list.

## Registry set and baseline

- `agents.yaml` entries (10): `hmda`, `ecoa`, `hvcre`, `hpml`, `trid`, `fzd`, `ybs`, `vmi` (eight evaluator-backed domains), `auditor` (evaluator-backed, cross-regime), `narrative` (prompt-only, markdown). `prompts/` has the same ten keys; every domain and the auditor declare `Tool: <key>_evaluate`.
- All eight domains use one adapter shape (`TOOL`, `tool_arguments`, `unavailable`, `extras`; `compliance_common/adapter.py` or an identical hand-written copy in `hpml`, `trid`, `ybs`), one generic stdio server (`compliance_common/mcp_server.py`) and one runner (`agents/runner.py`). The auditor has its own adapter (payload `{loan_data, agent_results}`, `NARRATE_CASE = False`). The narrative role runs `run_plain_agent`.
- Baseline before any change: `python3 -m unittest discover -s tests` -> 306 tests OK, 3 skipped (opt-in live APOR, live Ollama/Gemma, live OpenAI); `python3 scripts/check_context.py` and `check_plan.py` pass (Python 3.12.3).
- Step 01 scratch probe (not a test): for the eight domains, `sample_loan.json` gave the same `decision_id` directly and over stdio. It did not exercise A2A or failure paths; executing the plan then found four runtime defects (G9, G10, G14, G15) that the initial probe could not see, all repaired. The matrix and gap table below are the final state.

### YBS reference (what "parity" means)

YBS is the only role with every row below proven. Evidence keys used in the matrix:

| Key | Proof |
|---|---|
| Y1 | stdio discovery, call and child-process cleanup: `tests/test_mcp_client_stdio.py`; direct = in-process = stdio decision: `tests/test_mcp_contract.py`, `tests/test_ybs_evaluator.py::test_all_provider_and_mcp_tools_share_one_contract_and_decision` |
| Y2 | argument pinning, harness fallback, narrative-input `Unable To Determine` with no tool call, unparseable output, guard stripping: `tests/test_agent_runner.py::AgentRunnerTests` |
| Y3 | seeded mode, regulation text and provenance in the result, switch-off: `tests/test_agent_runner.py::ToolModeAndRegulationTests` |
| Y4 | contradiction watchdog, ungrounded-fact rejection, deterministic fallback, code-owned blocks: `ContradictionWatchdogTests`, `FactCheckTests`, `NarrativeSchemaTests` in `tests/test_agent_runner.py` |
| Y5 | Agent Card fields and A2A task artifacts (`agent_result`, `decision`) over ASGI: `tests/test_a2a.py::test_agent_card_and_tool_backed_task` |
| D1 | `tests/test_agent_runner.py::AllToolBackedAgentsTests` - each tool-backed registry key (eight domains) runs end to end on `sample_loan.json` in model mode against its in-process server; asserts classification, compliance result, extras key, trace, `agent_metadata.decision_id == decision.decision_id`, `tool_calls` |
| D2 | direct = in-process MCP `decision_id` parity: `tests/evaluator_contract.py::test_mcp_parity` (ecoa, fzd, hmda, vmi, hvcre, auditor), `test_replay_and_mcp_parity` in `tests/test_hpml_evaluator.py` and `tests/test_trid_evaluator.py` |
| D3 | per-domain regulation text contains its own rules; auditor has none: `test_every_tool_backed_agent_is_given_regulation_text_that_contains_its_own_rules` |
| A1 | `tests/test_agent_runner.py::AuditorAgentTests` (auditor tool call over assembled results), `tests/test_auditor_evaluator.py::test_failed_agents_are_reported_as_missing` (adapter level) |
| B1 | `tests/test_batch_concurrency.py` - bound of one, overlap above one, auditor last, result key order, `elapsed_seconds` |
| P1 | `tests/test_agent_parity.py::TransportParityTests` (step 02) - per registry role: stdio discovery and call with bounded child cleanup, direct = in-process = stdio = A2A `decision_id`/classification/compliance result, `<domain>` extras and trace, provenance ids, Agent Card name/version/skill/tags |
| P2 | `PinnedArgumentsTests` - a tampered valid case and an empty case from the model never change the decision (domains and auditor) |
| P3 | `MissingInputTests` - absent case, non-object case, narrative string: `Unable To Determine`, no tool call, no model call, `deterministic_no_input` (domains); no `agent_results` (auditor) |
| P4 | `InvalidCaseTests` - an evaluator-rejected case raises with the evaluator's own message and fails the A2A task with it (domains and auditor) |
| P5 | `ToolModeTests` - seeded and harness fallback reach the same decision, schema-constrained final answer, invalid `tool_mode` rejected |
| P6 | `NarrativeGuardTests` - model-authored decision fields stripped and reported, ungrounded narrative rejected twice then code-written, unparseable text keeps the raw text, regulation provenance kept (domains) or empty (auditor) |
| P7 | `PayloadFidelityTests` - an A2A request carrying `payload_json` yields the direct decision id; the legacy Struct-only request still works but drifts; malformed JSON fails the task |
| P8 | `AuditorRoleTests` - a failed upstream agent is missing, never reviewed; no case in the auditor narration prompt; dispatch |
| S1 | `tests/test_a2a.py::EveryRegisteredRoleTests` (step 03) - card per `agents.yaml` entry derived from its prompt (tool-backed vs LLM-only), unique URLs, result + decision artifacts for tool-backed roles, result + report for the narrative with no decision or tool calls, prose answer keeps raw text and parse error, registry options reach the executor |
| S2 | `tests/test_batch_concurrency.py::WholeRegistryBatchTests` - default selection from the registry, bounded concurrency over all domains, selection order and unknown-key rejection, failure isolation, real auditor adapter marks failed domains missing, failed auditor/narrative visible, narrative after auditor with failure evidence |
| S3 | `BatchCommandTests` - narrative opt-in, written after the auditor, a failed narrative exits 1 with no empty report and the batch JSON kept |
| S4 | `RegistryOptionsTests` - `serve_one` passes only documented options; shipped registry options valid |
| N1 | `tests/test_a2a.py::test_plain_agent_and_markdown_agent` (markdown artifact, no decision, no parsed JSON) and `::test_backend_failure_is_a_failed_task_not_a_crash` |

## Capability matrix (R1)

Cell values: `V <keys>` verified by the cited proof; `G<n>` gap, listed below (the cell is not verified); `N/A` not applicable for the stated reason. Rows are the capabilities; columns are the registry entries. The eight domains differ only in case key, evaluator and rule pack, and `tests/test_agent_parity.py` runs every claim for each of them, so a domain cell shows the same keys.

| Capability | hmda | ecoa | hvcre | hpml | trid | fzd | vmi | ybs | auditor | narrative |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 Registry entry, prompt header, Agent Card fields | V P1, S1 | V P1, S1 | V P1, S1 | V P1, S1 | V P1, S1 | V P1, S1 | V P1, S1 | V Y5, P1, S1 | V P1, S1 | V S1 (card says LLM-only, no tool tag) |
| C2 A2A task returns result and decision artifacts | V P1 | V P1 | V P1 | V P1 | V P1 | V P1 | V P1 | V Y5, P1 | V P1 | V N1, S1 (markdown report artifact; no decision by design) |
| C3 Canonical input mapped from payload; tool call pinned to it | V D1, P2 | V D1, P2 | V D1, P2 | V D1, P2 | V D1, P2 | V D1, P2 | V D1, P2 | V D1, Y2, P2 | V A1, P2 | N/A no tool; input is the other agents' results |
| C4 Missing canonical input -> `Unable To Determine`, no model call | V P3 | V P3 | V P3 | V P3 | V P3 | V P3 | V P3 | V Y2, P3 | V P3 | N/A no deterministic decision to withhold |
| C5 MCP stdio server: discovery, call, child cleanup | V P1 | V P1 | V P1 | V P1 | V P1 | V P1 | V P1 | V Y1, P1 | V P1 | N/A no MCP tool |
| C6 Direct = in-process MCP = stdio = A2A decision | V D2, P1, P7 | V D2, P1, P7 | V D2, P1, P7 | V D2, P1, P7 | V D2, P1, P7 | V D2, P1, P7 | V D2, P1, P7 | V Y1, Y5, P1, P7 | V D2, P1 | N/A no decision |
| C7 Tool mode `model` (tool called by model) | V D1 | V D1 | V D1 | V D1 | V D1 | V D1 | V D1 | V D1, Y2 | V A1 | N/A |
| C8 Tool mode `seeded`; harness fallback when the model skips the tool | V P5 | V P5 | V P5 | V P5 | V P5 | V P5 | V P5 | V Y2, Y3, P5 | V P5 | N/A |
| C9 Provenance: decision id, rule pack, evaluator, regulation text given | V D1, D3, P6 | V D1, D3, P6 | V D1, D3, P6 | V D1, D3, P6 | V D1, D3, P6 | V D1, D3, P6 | V D1, D3, P6 | V Y3, P6 | V A1, P6 (ids); N/A regulation text: cross-regime consolidation of other results, its pack has no regulatory source (D3) | N/A no decision record; narrative cites source results only |
| C10 Narrative guards: decision-owned fields stripped, fact check, retry, deterministic fallback | V P6 | V P6 | V P6 | V P6 | V P6 | V P6 | V P6 | V Y2, Y4, P6 | V P6 | N/A prose-only role; output is not decision-owned (see "Role differences") |
| C11 Model/tool failure is a visible failed task or flagged result, not a crash | V P4 | V P4 | V P4 | V P4 | V P4 | V P4 | V P4 | V P4, N1 | V P4, P8 | V N1, S1, S3 (failed narrative stage exits 1) |

Cells marked P7 are proven through the production client, which sends the exact payload as `payload_json` (G15).

## Orchestration capabilities (R3)

| Capability | Status | Proof / gap |
|---|---|---|
| O1 Domain set derived from the registry (`domain_keys`), explicit selection, unknown key rejected | V S2 | default = the eight registry domains; selection keeps the given order; unknown or unconfigured keys raise |
| O2 Bounded concurrency | V B1, S2 | bound 1 and 3 over the whole registry; peak equals the bound |
| O3 Auditor runs after every selected domain | V B1, S2 | all eight domains then the auditor, never the narrator by default |
| O4 A single failing domain agent is visible and does not sink the batch | V S2 | failed result keeps `parse_error` and `elapsed_seconds`; other domains and the auditor still run |
| O5 A failed domain reaches the auditor as missing, never as a pass | V A1, S2 | the real auditor adapter lists the failed domains in `failed_agents` and reviews only the rest |
| O6 Optional narrative runs after the auditor and only when requested | V S2, S3 | |
| O7 Failed narrative stage is visible | V S2, S3 | repaired (G9) |
| O8 Narrative input retains per-agent failure evidence | V S2 | repaired (G10) |
| O9 Raw text, parsed result and parse error retained for each role | V N1, S1, S2, P6 | tool-backed: raw model text, parsed, decision, guard; plain: raw text with parse error; failed: `parse_error` |
| O10 `agents.yaml` options reach the executor; local URLs launched per entry | V S1, S4 | |
| O11 Cards and tasks for every registered role | V P1, S1 | all ten registry entries |

## Role differences (not defects by default)

- **Domains:** classification vocabularies and `<domain>_evaluation` / `threshold_evaluation` extras differ by design; parity is judged on each domain's own `decision_id`, `final_classification`, `compliance_result` and its extras key, never on a shared schema.
- **Auditor:** evaluator-backed, but its input is the assembled results of the other agents (`agent_results`) rather than a `<domain>_case`; it narrates without the case (`NARRATE_CASE = False`), has no regulation text, and records failed or missing agents instead of pinning a loan case. It is tested as a role, not as a domain.
- **Narrative:** prompt-only, markdown output, no tool, no decision record and no deterministic guard. It must not be required to emit decisions, MCP results, seeded mode or regulation text. Its contract is: consume other agents' results, return markdown in `raw_text`/`report`, fail visibly.
- **YBS pilot policy:** YBS thresholds are institution-pilot policy; no other domain inherits them.

## Gaps and dispositions

Step 02 added `tests/test_agent_parity.py` (8 domains + auditor, offline) and made two shared-runtime repairs (G14, G15 server half). Step 03 added role and orchestration tests to `tests/test_a2a.py` and `tests/test_batch_concurrency.py` and made three repairs (G15 client half, G9, G10).

| Id | Gap | Evidence / basis | Affected paths | Test | Step | Disposition |
|---|---|---|---|---|---|---|
| G1 | No stdio test (discovery, call, bounded child cleanup) for any domain except YBS; auditor untested over stdio | `tests/test_mcp_client_stdio.py` was YBS-only | `tests/test_agent_parity.py` | P1 | 02 | resolved (tests; no runtime change needed) |
| G2 | Canonical-argument pinning proven only for YBS | `AgentRunnerTests` | `tests/test_agent_parity.py` | P2 | 02 | resolved (tests) |
| G3 | Missing canonical case behavior proven only for YBS | `test_narrative_input_is_unable_to_determine` | `tests/test_agent_parity.py` | P3 | 02 | resolved (tests) |
| G4 | Seeded mode and harness fallback proven only for YBS | `ToolModeAndRegulationTests` | `tests/test_agent_parity.py` | P5 | 02 | resolved (tests) |
| G5 | Narrative guard, ungrounded-fact rejection, deterministic fallback, `regulations_given` proven only for YBS | `ContradictionWatchdogTests`, `FactCheckTests` | `tests/test_agent_parity.py` | P6 | 02 | resolved (tests) |
| G6 | Agent Card and A2A task proven only for YBS | `tests/test_a2a.py` | `tests/test_agent_parity.py`, `tests/test_a2a.py` | P1, S1 | 02, 03 | resolved (tests; all ten registry roles, narrative role-specifically) |
| G7 | Auditor role contract untested beyond runner and adapter | `AuditorAgentTests` | `tests/test_agent_parity.py` | P1-P6, P8 | 02 | resolved (tests, role-specific payload) |
| G8 | Batch selection, unknown-key rejection, failure isolation and failed-agent-to-auditor handling untested | `tests/test_batch_concurrency.py` | `tests/test_batch_concurrency.py` | S2 | 03 | resolved (tests; no runtime defect found in selection, concurrency, ordering or isolation) |
| G9 | Suspected defect: a failed narrative stage produced an empty report that `cli._batch` reported as written | reproduced 2026-11-06 with a failing fake narrator: the report file existed with `''` and stderr said "Narrative report written" | `orchestrator/cli.py` | S2, S3 | 03 | resolved (repair + test): a failed narrative prints "NOT written" with the reason, writes no report and exits 1 after the batch JSON is saved. Behavior note: this is a new non-zero exit status for a failed optional stage |
| G10 | Suspected defect: `_as_text_or_parsed` sent `""` for a failed agent to the narrative (and the auditor), losing the failure evidence | reproduced 2026-11-06: narrative input was `{'hmda': ''}` | `orchestrator/batch.py` | S2 | 03 | resolved (repair + test): a failed agent is `{agent_key, status: failed, failure}`; the auditor adapter still classes it as failed (no `domain_determination`), raw text and parsed results are passed as before |
| G11 | Registry options plumbing (`serve_one` filters keys) and per-role applicability untested | `orchestrator/launcher.py` | `tests/**` | S1, S4 | 03 | resolved (tests; options are meaningful only for tool-backed roles and are ignored by the plain narrative agent) |
| G12 | Operator documentation stale: README said "seven" agents, omitted TRID from the Agents table, and framed shared behavior under "Deterministic YBS pilot" | `README.md` | `README.md`, `docs/design/**` | check_context.py; wording reviewed against this matrix | 04 | documentation corrected (README intro, Agents table, shared-contract section with YBS specifics kept, batch failure behavior, test description; `registry-driven-a2a-orchestration.md` and `raw-and-parsed-results-retained.md` extended). Compliance-review caveats kept; no behavior claim is made beyond a cited proof |
| G13 | Live opt-in tests (Gemma, OpenAI smoke, live APOR) skipped by default | `tests/test_ybs_gemma_integration.py` et al. | none | - | - | not applicable: live model services are excluded by the spec; recorded, not run |
| G14 | Found in step 02. An evaluator rejection (invalid case) surfaced as `ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)`: the evaluator's reason was lost from the runner error and from the failed A2A task text, for every domain, over in-process and stdio | reproduced for hmda and ybs; `compliance_common/mcp_client.py` | `compliance_common/mcp_client.py` (unwrap to the first underlying error) | P4 | 02 | resolved (repair + test). Side effect: the runner's existing `except RuntimeError` fallback now also covers evaluator rejections (one deterministic retry by the harness, then the same error) |
| G15 | Found in step 02. A2A data parts are protobuf Structs, which turn every integer into a float (42 differences in `sample_loan.json`). For hmda, hpml, trid, vmi, ybs and the auditor the evaluator then returned a different `decision_id` and record text (for example `425000.0`) than direct evaluation of the same case; classification and result were unchanged. ecoa, fzd and hvcre were unaffected only because of their sample data | reproduced by round-tripping `sample_loan.json` through `new_data_part`/`MessageToDict`; failed R2 parity before the repair | `agents/a2a_server.py` (accept exact JSON text in `payload_json`; legacy fields still accepted), `orchestrator/a2a_client.py` (send `payload_json` beside `payload`) | P7 | 02 (server), 03 (client) | resolved (repair + test): the production client delivers every domain and auditor payload exactly; an older Struct-only client still works but is not decision-identical, which is tested and documented |

No cell above is labeled verified without a cited proof. G9 and G10 were reproduced before repair (see their rows).

## Disposition log

Updated as steps execute: each gap moves from `open` to `resolved (test names)`, `resolved (repair + test)`, `documentation corrected`, `not applicable (reason)` or `escalated`.

- 2026-11-06, step 02: G1-G5, G7 resolved by tests; G6 partly; G14 resolved by repair; G15 server half resolved, client half assigned to step 03.
- 2026-11-06, step 03: G6, G8, G11 resolved by tests; G9, G10 reproduced then repaired; G15 client half repaired. Remaining open: G12 (documentation, step 04).
- 2026-11-06, step 04: G12 documentation corrected. Every gap is resolved, documentation-corrected or not applicable (G13); no cell is unknown.
