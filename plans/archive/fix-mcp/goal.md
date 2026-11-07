---
gist: "Read when: running the approved fix-mcp plan with a Claude Code goal or resuming its execution."
---

# MCP repair goal and execution protocol

This completed plan has been archived. The command below records its original execution location.

From the repository root on the `fix-mcp` branch, start Claude Code and enter:

```text
/goal Execute the approved plans/fix-mcp plan using plans/fix-mcp/goal.md. Continue until the plan is verified complete or a plan-defined escalation requires my decision. Report which outcome occurred and the supporting evidence; do not report an escalation as completion.
```

The goal drives successive turns in the current session; it does not give each turn a fresh context window. The plan and step files are the durable execution record, so reread them when resuming or after context compaction. The goal evaluator judges the transcript; it does not independently run gates or inspect files.

## Execution

1. Follow `AGENTS.md`, then read this plan's `spec.md` and the current front matter of all `steps/*.md`. Verify that the spec is approved. Inspect the working tree and preserve existing work, including the OpenAI provider tests inherited from the `openai` branch.
2. Resume any `in_progress` step before selecting another. Otherwise select one `pending` step whose `depends_on` steps are all `done`. Work serially on one step at a time; a step may take more than one goal turn. Inspect the relevant implementation before assuming anything is missing.
3. Mark the selected step `in_progress`. Work within its `touches` and the spec's delegated authority. Run the exact step gate and any additional checks required by its completion criteria. For step 01, the named gate in the working environment does not replace its clean-environment compatibility check.
4. Record the date, commands, results, and required versions in the step's `evidence:` field. Mark the step `done` only when its gate and all completion criteria pass. A timeout, missing prerequisite, or unavailable check is not a pass. Diagnose and repair ordinary failures within scope; preserve protected checks.
5. Continue with the next eligible step. Step 04 runs the spec's combined validation after the preceding steps. Record the actual results in its evidence. Verify all requirements and protected checks in `spec.md`, all steps are `done` with evidence, and the combined validation passed. Only then set the spec status to `complete` and report the evidence in the conversation.

Do not execute or complete the separate `plans/openai` plan as part of this goal. Its blocked step is expected; report any remaining OpenAI work as follow-up, without treating it as completion of the MCP plan.

## Stop and handoff

If the spec is not approved, a spec-defined escalation occurs, a required action exceeds delegated authority, or no eligible work can proceed, stop work and report the concrete decision or blocker. For a blocked step, set `status: blocked` and preserve the attempted commands, outcomes, and relevant versions in its evidence. Leave the spec incomplete. In particular, do not use the network to work around missing local dependency distributions; report the clean-environment gate as blocked.

Surface either verified completion or the blocker in the conversation so the goal evaluator can see the outcome. The evaluator is model-based and may not stop exactly as intended; if it continues after an escalation, clear the goal with `/goal clear` and resume only after the decision is recorded. Do not weaken a check or label a blocked plan complete to terminate the goal.

Do not push, publish, change remotes, or create commits unless separately authorized. A human can review and merge the repair into `openai` after the MCP plan is complete, then resume the OpenAI plan and rerun its original gate.
