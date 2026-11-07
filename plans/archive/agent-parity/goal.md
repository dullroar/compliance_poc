---
gist: "Read when: executing or resuming the approved YBS-based agent parity plan with any coding assistant."
---

# Agent parity execution protocol

The plan can be executed by any coding assistant. After confirming spec approval, give the assistant this ordinary prompt from the repository root:

```text
Execute the approved plans/agent-parity plan using plans/agent-parity/goal.md. Continue until the plan is verified complete or a plan-defined escalation requires my decision. Report which outcome occurred and supporting evidence; do not report an escalation as completion.
```

Execution and verification are the assistant's responsibility; no platform-specific goal feature or evaluator is required. Reread the spec, inventory and step front matter after resuming or a context reset.

1. Follow `AGENTS.md`, verify approval, inspect the working tree and preserve existing work. Discover the actual registered roles and YBS implementation before drawing conclusions about gaps.
2. Resume `in_progress` work first, otherwise select the next pending step with dependencies done. Work serially within the step's `touches` and the spec's delegated authority; record actual outcomes in evidence and dispositions in the inventory.
3. Repair ordinary integration failures inside scope and preserve domain-specific behavior. Do not silently classify unknown coverage as verified, require narrator-specific features of every role, or alter regulatory decisions.
4. Run the exact combined gate. Verify every role, applicable requirement, protected check and gap disposition; mark each step done only with evidence and the spec complete only when all pass.

If approval is missing, no eligible work can proceed, a protected check cannot pass, or the plan requires a decision, block the affected step and report the concrete blocker and evidence. Do not call an escalation completion. Surface completion or the blocker in the conversation. Do not push, publish or commit without separate authorization.
