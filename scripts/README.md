# Scripts

Deterministic automation. Reuse these before writing new tooling.

See [AGENTS.md](./AGENTS.md) for the generated script index. Run `python3 scripts/check_context.py`
to check generated indexes, active plans, local links and context files for secrets.

`python3 scripts/build_context_indexes.py` still works as an index command.
`python3 scripts/scan_context_secrets.py` still runs the context secret scan.
* [openai_cost_estimator.py](./openai_cost_estimator.py). Read when: before any OpenAI API call; checks supported pricing and the cumulative budget but does not reserve funds.
* [anthropic_cost_estimator.py](./anthropic_cost_estimator.py). Read when: before any Anthropic API call; estimates supported calls and manages reservations against a separate cumulative budget.

For the Anthropic estimator, start with `python3 scripts/anthropic_cost_estimator.py --help`.
`estimate` reports a conservative bound using the maximum input and output tokens per attempt and all
possible attempts, including retries. The initial ledger records prior spend as unknown; use `baseline`
only after reconciling that spend. `reserve` records the bound before a call, and `settle` records a
verified total afterward. Leave the reservation outstanding if usage is unknown. These commands do not
enforce token or retry limits inside the API client and do not authorize a live call.
