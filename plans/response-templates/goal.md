---
gist: "Read when: executing or resuming the approved response-templates plan."
---

# Response templates - goal and execution protocol

Once the spec status is `approved`, from the repository root enter:

```text
/goal Execute the approved plans/response-templates plan using plans/response-templates/goal.md. Continue until the plan is verified complete or a plan-defined escalation requires my decision. Report which outcome occurred and supporting evidence; do not report an escalation as completion.
```

1. Follow `AGENTS.md`; inspect the working tree and preserve existing work. Use the repository `.venv`. Branch before editing; do not commit or push without separate authorization.
2. Steps 02 and 03 are independent (different `touches`) and may run in separate lanes. Everything else is serial. Reread the spec and step front matter after resuming.
3. Write each protected test before the code it protects. Never loosen a limit to get green: a limit that cannot be met is an escalation (spec, Escalate when).
4. Step 03 ends with a stop: record the measured word counts and the proposed final limits, then ask Jim to confirm them before step 04 starts.
5. Step 06 live run: only after the spending preflight (`scripts/anthropic_cost_estimator.py estimate`, then `reserve`), a rate and date recheck, and the zero-retry, finite-timeout guards of the existing gate. A skip, fallback or truncation is not live success.
