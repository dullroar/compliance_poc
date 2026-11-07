---
gist: "Read when: executing or resuming the approved live Anthropic and OpenAI runs of the agent-parity improvements."
---

# Live parity runs - goal and execution protocol

Once the spec status is `approved`, with `claude-haiku-5-5` and `gpt-6-luna` and a separate cumulative USD $20 budget per provider, from the repository root enter:

```text
/goal Execute the approved plans/live-parity plan using plans/live-parity/goal.md. Continue until the plan is verified complete or a plan-defined escalation requires my decision. Report which outcome occurred and supporting evidence; do not report an escalation as completion.
```

The goal drives successive turns in the current session, not fresh context windows, and its evaluator does not run checks or read files. Reread the spec and step front matter after resuming or compaction.

1. Follow `AGENTS.md`; inspect the working tree and preserve existing work. Use the repository `.venv`; record Python and SDK versions. Never print credentials, `.env` contents, or raw request/response bodies.
2. Resume `in_progress` work first; otherwise run every pending step whose dependencies are done. Steps 02/03 and 04/05 are independent lanes (no shared `touches`, separate ledgers) and may run in separate lanes or serially. Never run two live runs against the same ledger at once.
3. Before each live run verify, in order: spec approval; opt-in variable; credentials present (names only); synthetic-only outbound data; pricing check date; the provider's preflight estimator; a durable reservation covering every possible request; guard limits in the actual client (zero SDK retries, finite timeout, request and byte caps). If the Anthropic baseline is still `baseline_unknown`, block step 04 and report; step 05 continues.
4. Record every request, retry and guard retry. Retain the full reservation whenever usage or cost is unknown. Repeat a failed run only after in-scope diagnosis and only if its worst-case bound fits the remaining cumulative budget.
5. Run the exact combined validation. Mark a step `done` only with its gate passing and evidence recorded. Mark the spec `complete` only when both non-skipped live runs and all protected checks pass.

If approval, credentials, a baseline, rates or budget are missing, or a protected check cannot pass, mark the affected step `blocked`, keep the evidence, and report the concrete decision needed. A skip, timeout, fallback or fake is not live success. Do not push, publish or commit without separate authorization. Never set `RUN_LIVE_*` variables when running the full suite.
