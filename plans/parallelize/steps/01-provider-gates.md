---
id: 01-provider-gates
status: pending
depends_on: []
touches:
  - orchestrator/batch.py
  - orchestrator/config.py
  - orchestrator/cli.py
  - agents.yaml
  - tests/test_batch_concurrency.py
lane: gates
gate: python3 -m unittest tests.test_batch_concurrency -v
requirements: [R1, R2, R3, R6]
evidence: ""
---

# Give remote and local agents separate concurrency gates

Write for an agent with no chat history.

## Change

- Resolve each agent's provider (entry, CLI `--provider`, `COMPLIANCE_PROVIDER`, default anthropic). One gate of width 1 for `ollama`; one gate of width `remote_concurrency` (committed default 2) for `anthropic` and `openai`. Keep `concurrency` and `--concurrency` semantics (spec R1). Add `--remote-concurrency`.
- Keep `gather` and registry-order results. Count roles that failed on rate limits and print it in the verbose summary.
- Tests first: per-class peaks, serial override, randomized-latency ordering across seeds, one failing role, one rate-limited role (R1-R3). Update the `agents.yaml` header comment.

## Do not change

Agent output, the auditor and narrative ordering, the A2A client and server, the live harness.

## Dependencies already satisfied

- None.

## Completion criteria

New and existing batch tests pass. The committed `agents.yaml` behaves serially for a local provider and in parallel for a remote one, with no per-run flag.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
