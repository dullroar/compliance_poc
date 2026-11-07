---
gist: "Read when: running or resuming the approved OpenAI provider plan with a Claude Code goal."
---

# OpenAI provider goal and execution protocol

From the repository root on a branch containing the MCP repair, start Claude Code and enter:

```text
/goal Execute the approved plans/openai plan using plans/openai/goal.md. Continue until the plan is verified complete or a plan-defined escalation requires my decision. Report which outcome occurred and the supporting evidence; do not report an escalation as completion.
```

The goal drives successive turns in the current session; it does not start a fresh context window on each turn. The plan and step files are the durable execution record: reread them after resuming or context compaction. The goal evaluator judges the transcript and does not independently run gates or inspect files.

## Execution

1. Follow `AGENTS.md`, read this plan's `spec.md` and the current front matter of all `steps/*.md`, and verify that the spec is approved. Inspect the working tree and preserve existing work. Check the archived MCP repair plan and the implementation before assuming that the recorded blocker is resolved.
2. The original step 03 gate was blocked by the MCP lifecycle failure. The repair is recorded in `plans/archive/fix-mcp/`; on a checkout containing that repair, recheck the blocker and resume step 03 by setting it to `in_progress` while retaining its prior evidence. If the repair is absent or the blocker persists, keep the step blocked and report the evidence instead of trying to perform the separate MCP plan.
3. Run the named step 03 gate and all its completion criteria. Use the repository virtual environment for `python3` commands, for example by exporting `PATH="$PWD/.venv/bin:$PATH"` in the shell that runs the gates; verify the interpreter and report its version. Preserve the named commands and test coverage. A timeout may wrap a gate to detect a hang, but it is a failure signal, never a pass.
4. Record the date, exact commands, interpreter and results in the step's `evidence:` field, retaining the prior failure history. Mark step 03 `done` only when its gate and completion criteria pass. Diagnose ordinary failures within the approved scope; if a protected check fails or an escalation condition occurs, stop and report it.
5. Continue serially with each eligible step, resuming `in_progress` work before selecting a `pending` step whose dependencies are all `done`. A step may take multiple goal turns. Inspect the relevant implementation before assuming work is missing. Work within the step's `touches` and the spec's delegated authority.
6. Run step 04's exact combined gate with the virtual environment selected. Record its actual results and the absence of any separately authorized live smoke test. Verify every requirement and protected check in the spec and that all steps are `done` with evidence. Only then set the spec status to `complete` and report the evidence in the conversation.

Do not make a live OpenAI call, use real records, change evaluator decisions, weaken protected checks, or change the default provider or model. A live smoke test requires separate authority and is not a substitute for the offline checks.

## Stop and handoff

If the spec is not approved, a spec-defined escalation occurs, an action exceeds delegated authority, or no eligible work can proceed, stop and report the concrete decision or blocker. Set an affected step to `blocked` and retain attempted commands, results, and relevant versions in its evidence; leave the plan incomplete. Do not label missing verification or a timeout as passing.

Surface verified completion or the blocker in the conversation so the goal evaluator can see the outcome. The evaluator is model-based and may not stop exactly as intended; if it continues after an escalation, clear the goal with `/goal clear` and resume only after the decision is recorded. Do not weaken a check or label a blocked plan complete to terminate the goal.

Do not push, publish, change remotes, or create commits unless separately authorized.
