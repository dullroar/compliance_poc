---
gist: "Read when: executing or resuming the approved tune-ais plan."
---

# Tune AIs - goal and execution protocol

Once the spec status is `approved` and plans `response-templates` and `parallelize` are `complete`, from the repository root enter:

```text
/goal Execute the approved plans/archive/tune-ais plan using plans/archive/tune-ais/goal.md. Continue until the plan is verified complete or a plan-defined escalation requires my decision. Report which outcome occurred and supporting evidence; do not report an escalation as completion.
```

1. Follow `AGENTS.md`; inspect the working tree and preserve existing work. Use the repository `.venv`. Branch before editing; do not commit or push without separate authorization.
2. Steps are serial. Step 02 ends with a stop: Jim confirms the bar and scenarios before step 03.
3. Before every live call: spec approval, credentials present (names only), synthetic data only, rate and date recheck, `anthropic_cost_estimator.py estimate` and `reserve`, zero SDK retries, finite timeout, request and byte caps. Never run two live runs against the same ledger at once. Retain a reservation when usage is unknown.
4. Climb the ladder by role, cheapest rung first. Stop a role at its first passing rung. Record every rung tried.
5. Step 04 ends with a stop: present the floor and the proposed `agents.yaml` changes. Do not apply them without Jim's decision.
