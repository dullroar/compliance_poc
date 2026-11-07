---
gist: "Read when: executing or resuming the approved OpenAI synthetic live smoke-test plan with a goal."
---

# OpenAI smoke-test goal and execution protocol

With `gpt-6-luna` and the cumulative $20 budget approved, from the repository root enter:

```text
/goal Execute the approved plans/openai-smoketest plan using plans/openai-smoketest/goal.md. Continue until the plan is verified complete or a plan-defined escalation requires my decision. Report which outcome occurred and supporting evidence; do not report an escalation as completion.
```

The goal drives successive turns in the current session, not fresh context windows. The goal evaluator does not independently run checks or inspect files. Reread the spec and step front matter after resuming or compaction.

1. Follow `AGENTS.md`; inspect the working tree and preserve existing work. Verify spec approval, the selected model, cumulative ledger and spend bound before live calls. Use the repository environment and verify Python and SDK versions. Never reveal credentials.
2. Resume `in_progress` work first; otherwise select the next pending step whose dependencies are done. Execute serially within its `touches` and delegated authority. Record exact checks and actual results, retaining prior evidence.
3. Before each live cycle verify opt-in, approved model, credentials, synthetic-only outbound data, request cap, current rates and the persistent cumulative budget. Reserve worst-case request costs before submission and retain reservations for unknown usage. Repeat failed cycles only after in-scope diagnosis and only when the next cycle fits the remaining budget. Record request usage and per-mode/cycle totals; capture no raw responses or keys.
4. Run the exact combined validation and verify each protected check. Set a step to `done` only when its gate and criteria pass with evidence; mark the spec `complete` only after all requirements and steps pass, including a non-skipped live run.

If approval or prerequisites are missing, a protected check cannot pass, or the plan's escalation condition occurs, mark the affected step `blocked`, retain the evidence and report the concrete decision needed. A skip, timeout, fallback, or offline fake is not live success; preserve its usage or conservative reservation in the ledger. Surface completion or the blocker in the conversation; if the goal continues after escalation, use `/goal clear`. Do not push, publish or commit without separate authorization.
