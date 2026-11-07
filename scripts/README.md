# Scripts

Deterministic automation. Reuse these before writing new tooling.

* [check_context.py](./check_context.py). Read when: you changed any context file (AGENTS.md, docs, memory, plans); runs every check below.
* [build_context_indexes.py](./build_context_indexes.py). Read when: you added or re-gisted a routed Markdown file; regenerates README indexes (`--check` verifies only).
* [check_plan.py](./check_plan.py). Read when: you created or changed a plan or step; validates dependencies, write-scope overlap, traceability and prints derived status.
* [check_links.py](./check_links.py). Read when: you moved or renamed a Markdown file; verifies local links and anchors.
* [scan_context_secrets.py](./scan_context_secrets.py). Read when: you added examples, logs or paths to context files; flags credentials and personal paths.
* [ctx_common.py](./ctx_common.py). Read when: editing the context scripts; shared front-matter parsing and file discovery.
* [openai_cost_estimator.py](./openai_cost_estimator.py). Read when: before any OpenAI API call; checks supported pricing and the cumulative budget but does not reserve funds.
* [anthropic_cost_estimator.py](./anthropic_cost_estimator.py). Read when: before any Anthropic API call; estimates supported calls and manages reservations against a separate cumulative budget.

For the Anthropic estimator, start with `python3 scripts/anthropic_cost_estimator.py --help`.
`estimate` reports a conservative bound using the maximum input and output tokens per attempt and all
possible attempts, including retries. The initial ledger records prior spend as unknown; use `baseline`
only after reconciling that spend. `reserve` records the bound before a call, and `settle` records a
verified total afterward. Leave the reservation outstanding if usage is unknown. These commands do not
enforce token or retry limits inside the API client and do not authorize a live call.
