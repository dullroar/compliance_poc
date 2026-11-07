---
id: 04-floor-report
status: done
depends_on: [03-live-sweep]
touches:
  - plans/archive/tune-ais/floor.md
  - memory/model-floor.md
  - README.md
lane: report
gate: python3 scripts/check_context.py && python3 scripts/check_plan.py
requirements: [R2, R4, R6]
evidence: "2026-11-07: python3 scripts/check_context.py and python3 scripts/check_plan.py ok. Artifacts: plans/archive/tune-ais/floor.md (per role: lowest passing rung = 0 (code only) for all ten roles; cost per successful narrative USD 0 at rung 0, Haiku 5.5 templates: code rung measured separately with cost, tokens, latency; date, pricing source, ledger rows, what was not tested, re-run commands, distrust date 2027-02-07 inferred), memory/model-floor.md (gist, one paragraph, re-run command, distrust date), README note on the command. T5: sample of 12 chosen by script (seed tune-ais-t5-v1) from rung 0, so all code-written (HMDA 4; ECOA, HVCRE, HPML, TRID, FZD, YBS, VMI, auditor 1 each); Jim read all 12 on 2026-11-07: 12 of 12 acceptable (one observation, not a rejection: HPML-ESCROW's Condition repeats the Requirement). Proposal presented, Jim's decision recorded: agents.yaml UNCHANGED; plan a separate no-model option (not started here). Proposed and not applied: templates: code for the 7 roles that cleared rung 1, or for all nine tool roles. Gaps stated in floor.md: rung 0 has no agents.yaml setting; rung 1 under templates: model not measured; T5 reads cover code-written paragraphs only; thinking-token billing unverified; one workload, synthetic data."
---

# Write the dated floor, get the T5 reads, and propose config changes

Write for an agent with no chat history.

## Change

- Select the T5 paragraph sample by script from the cheapest passing rung and give it to Jim for the 12 reads; record each answer.
- Write `floor.md` (per role: lowest passing rung, cost per successful narrative, tokens, latency, date, pricing source, ledger rows, what was not tested). Add `memory/model-floor.md` (gist line, one paragraph, the re-run command, the date after which to distrust it). README note on the command.
- Propose `agents.yaml` changes (per-role model, `templates: code` where rung 0 passes). **Do not apply them. Ask Jim.**

## Do not change

`agents.yaml`, provider defaults, source.

## Dependencies already satisfied

- 03: the evidence.

## Completion criteria

Floor report and memory topic exist; context and plan checks pass. Jim has the proposal and the T5 result.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
