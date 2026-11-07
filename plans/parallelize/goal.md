---
gist: "Read when: executing or resuming the approved parallelize plan."
---

# Parallelize - goal and execution protocol

Once the spec status is `approved`, from the repository root enter:

```text
/goal Execute the approved plans/parallelize plan using plans/parallelize/goal.md. Continue until the plan is verified complete or a plan-defined escalation requires my decision. Report which outcome occurred and supporting evidence; do not report an escalation as completion.
```

1. Follow `AGENTS.md`; inspect the working tree and preserve existing work. Use the repository `.venv`. Branch before editing; do not commit or push without separate authorization.
2. Steps are serial. Step 02 must pass before step 03 may make any live call.
3. Before the step 03 live run: spec approval, credentials present (names only), synthetic data only, rate and date recheck, `anthropic_cost_estimator.py estimate` and `reserve`, the live gate's zero-retry and finite-timeout guards. Never run two live runs against the same ledger at once.
4. The width ramp is 2, then 4, then 8. Climb only while the previous width ran clean; on a non-cost error, record it and stop at the last clean width.
5. Do not set `RUN_LIVE_*` variables when running the full suite.
