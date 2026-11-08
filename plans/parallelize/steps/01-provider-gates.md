---
id: 01-provider-gates
status: done
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
evidence: "2026-11-07: python3 -m unittest tests.test_batch_concurrency -v -> 34 tests OK (about 3 s), run 4 times with no failure; full suite 550 tests OK (5 skipped, all RUN_LIVE_* unset), then 560 OK after step 02. Written tests first and seen red (2 failures, 41 errors) before the code. Change: orchestrator/batch.py run_batch(concurrency=None, remote_concurrency=None, local_concurrency=None, provider=None): one gate per provider class (ollama = local, width 1 from agents.yaml concurrency; anthropic and openai = remote, width remote_concurrency, default 2), an explicit concurrency is also an overall cap and alone keeps its old meaning (that many at once), so the existing tests pass unmodified; class gate is taken before the overall cap so a waiting agent never holds an overall slot. Provider = agents.yaml entry, else --provider, else COMPLIANCE_PROVIDER, else anthropic. config.load_settings adds remote_concurrency (default 2, must be >= 1); cli adds --remote-concurrency and _widths(); agents.yaml commits remote_concurrency: 2 and its header comment explains both keys. Verified: all-remote peak equals the width at 2, 4 and 8; all-local peak 1 whatever the remote width; mixed batch peaks per class (remote 4, local 1, together 5); explicit --concurrency 1 forces serial; 25 random-latency seeds with one failing role keep registry order, auditor last, narrative after the auditor ends; a role that fails with a 429 fails alone, others and the auditor complete, and the verbose summary says '1 role failed on rate limits: <role>' (retry-after logged when the error text has it). No new retry layer, no threads. Deviation: the committed concurrency: 1 is now the local width only, not an overall cap, because the plan requires remote agents to run in parallel with no per-run flag; an explicit --concurrency N on the command line still caps everything. Not verified: a live remote 429 (step 03)."
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
