---
gist: "Read when: planning or auditing parallel execution of the domain agents against remote providers, or changing batch concurrency, rate-limit handling or the request guards."
---

# Parallelize - specification and execution agreement

Status: complete (approved by Jim Lehmer, 2026-11-07; executed 2026-11-07, follow-up checks 2026-11-08; archived 2026-11-08; results in results.md). Decided by Jim 2026-11-07: start small and ramp the remote width 2, then 4, then 8, and back down if limits other than cost cause errors. Other rules marked inferred still need confirmation.

See [goal.md](goal.md) for the goal command.

## Goal and exclusions

Run the eight domain agents at the same time when their model provider is a remote one (Anthropic or OpenAI), and keep everything else as it is: the auditor runs after all domain agents, the narrative role runs after the auditor, and local Ollama agents stay serialized.

What exists today ([`orchestrator/batch.py`](../../../orchestrator/batch.py)): `run_batch` already fans the domain agents out with `asyncio.gather` behind one `asyncio.Semaphore`. The width comes from `concurrency` in `agents.yaml` (committed value 1) or `--concurrency`. So the change is not a new mechanism. It is (a) a per-provider width instead of one global number, and (b) the work needed to make that width safe against real remote APIs and the live-run accounting. No new threading model: asyncio stays, and the A2A server's existing `asyncio.to_thread` call stays as it is.

Expected gain, from the archived live run (Anthropic Haiku, model phase): domain agents took about 47 s in series (2.9 to 9.7 s each), so about 10 s in parallel. The auditor (6.5 s) and narrative role (70.8 s) cannot overlap with them, so the whole batch falls from about 124 s to about 87 s, roughly 30%. The narrative role dominates what is left; the `response-templates` plan is what shrinks it. Fact for the domain phase, inference for the total.

This work does NOT: parallelize the auditor or narrative role; change Ollama or any local-model behavior; add threads, processes or free-threaded or sub-interpreter Python; change what any agent computes; change models, prompts or rate budgets; or raise the live-run request caps.

## Requirements

### R1. Concurrency width is set per provider class, with safe defaults

- Basis: documented (current single `concurrency` setting in [`orchestrator/config.py`](../../../orchestrator/config.py)); inferred: defaults.
- Rule (inferred): agents whose resolved provider is `ollama` share one gate of width 1. Agents whose resolved provider is `anthropic` or `openai` share a gate whose width is `remote_concurrency` (committed default 2; settable in `agents.yaml` and by `--remote-concurrency`; the ramp to 4 and 8 is decided from step 03's measurements, not assumed). The existing `concurrency` key and `--concurrency` keep their meaning as the cap for local agents and as an overall cap when set explicitly, so existing configs behave as before. The resolved provider of an agent is its `provider` entry, else the CLI `--provider`, else `COMPLIANCE_PROVIDER`, else `anthropic`.
- Example: mixed config with seven Anthropic domain agents and one Ollama agent runs the seven together and the Ollama agent one at a time. An all-Ollama config runs one at a time, as today.
- Acceptance check: extend `tests/test_batch_concurrency.py` with fakes: all-remote peak equals the width (checked at 2, 4 and 8); all-local peak is 1; mixed peaks are per class; an explicit `--concurrency 1` forces serial.

### R2. Order and result shape are unchanged

- Basis: documented ([`tests/test_batch_concurrency.py`](../../../tests/test_batch_concurrency.py): the auditor always runs last; result keys keep registry order).
- Example: with all domain calls finishing out of order, `results` still lists domain roles in registry order, then `auditor`; the narrative role starts only after the auditor ends; a domain role that raises becomes a `parse_error` result and does not stop the others.
- Acceptance check: tests with randomized fake latencies and one failing role across many seeds.

### R3. Rate limits degrade gracefully

- Basis: documented (the Anthropic and OpenAI SDKs retry 408, 409, 429 and 5xx with backoff, default 2 attempts, in `Backend._make_client`); inferred: eight simultaneous requests of 5k to 46k input tokens can trip a per-minute token limit on a small account.
- Rule: no new retry layer. A 429 that survives the SDK retries fails that role only (R2), is logged with the provider's `retry-after` when present, and the batch summary says how many roles failed on rate limits. Back-down rule (Jim's decision): the committed default is the highest width in the ramp 2, 4, 8 that completes with no rate-limit or other non-cost errors; if a width errors, record the error text, the limit it names and the account tier, and fall back to the previous width.
- Acceptance check: fake backend raising a rate-limit error for one role: that role fails alone, the others and the auditor complete, the summary counts it.

### R4. Live-run accounting stays correct under concurrency

- Basis: documented ([live-parity spec R1](../live-parity/spec.md): request cap, byte bound, reservation, ledger; concurrency was fixed at 1 so accounting was deterministic; [`tests/live_parity_common.py`](../../../tests/live_parity_common.py) calls `run_batch(..., concurrency=1)`).
- Rule: the guarded clients must be safe for simultaneous calls (a lock around the cap check, counters and the metadata-only run-file and ledger writes), and an unexpected extra request must still be refused. The existing live gates keep `concurrency=1` unless a plan step sets otherwise; they must not change behavior. Parallel live measurement is opt-in (R5).
- Example: eight threads each ask for a request when two of the cap remain: exactly two proceed, six are refused, the ledger row count and totals are exact.
- Acceptance check: new offline tests in `tests/test_anthropic_live_accounting.py` and `tests/test_openai_live_parity_accounting.py` (concurrent stress with a fake transport; process-restart replay unchanged). The existing tests in both files stay unmodified and pass.

### R5. The speedup is measured, not assumed

- Basis: inferred.
- Rule: one opt-in live timing on Anthropic (`claude-haiku-5-5`, synthetic data) records wall time for the domain phase and the whole batch at width 1, then 2, then 4, then 8, on the same case, one run each, with per-role latency. It stops climbing at the first width that shows a rate-limit or other non-cost error and records that width as too high. OpenAI is measured only if Jim approves it separately.
- Acceptance check: `plans/archive/parallelize/results.md` with the table by width, the reservation and settlement of each run, rate-limit events, the percentage change, and the width chosen as the committed default. A smaller gain than 25% on the domain phase at the chosen width is recorded as a finding, not hidden.

### R6. Existing behavior and validation are undisturbed

- Basis: documented ([agent contract](../../../AGENTS.md)).
- Acceptance check: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`, all `RUN_LIVE_*` variables unset.

## Constraints and assumptions

- Each agent is its own A2A server process or ASGI app and starts its own MCP stdio evaluator subprocess per call, so agents share no state. Fact from `agents/a2a_server.py`, `compliance_common/mcp_client.py`. Eight simultaneous Python subprocess starts is a CPU burst on a laptop; step 03 records it.
- A remote account's rate limits are unknown. The ramp measures them. Jim confirms the account tier if an error names a limit.
- Local model use is out of scope, but the code must not make Ollama runs wider by accident (R1).
- Run order across plans (inferred): independent of `response-templates`, but both touch `orchestrator/batch.py` and `orchestrator/cli.py`; execute this plan after `response-templates` step 05, or serialize the shared files. `tune-ais` runs last.

## Domain challenge

- *Suspicious - explain it:* the domain agents share `logs/<component>.jsonl`. Resolution (inferred): each agent has its own component name, so files differ; step 02 verifies there is no interleaving within a file under load.
- *Suspicious - explain it:* the live harness reserves its worst case up front, then runs. Parallel calls cannot exceed that bound if the guard is locked (R4). Resolution: prove it by stress test before any live parallel run.
- *Suspicious - explain it:* faster is not always cheaper: prompt-cache hits from sequential calls could be lost. Resolution (inferred): the agents use different system prompts and regulation texts, so no cross-agent cache hits exist today; the live timing records cache tokens to confirm.
- *Contradicts a confirmed rule:* letting the auditor start early. It needs every domain result, and a missing result is never read as a pass.

## Delegated authority

- The executor MAY change `orchestrator/batch.py`, `config.py`, `cli.py`, `agents.yaml` comments and keys, the live guards and live accounting tests as R4 states, the README operator notes, and add offline tests. It MAY run the single Anthropic timing in step 03 after the spending preflight and a durable reservation, within the existing USD 20 Anthropic budget and a bound of USD 0.50 for this plan (four runs at about USD 0.07 each in the archive, plus margin for one repeat).
- The executor MUST NOT: add threads, processes or a new retry layer; change any agent's output; raise the request caps; run OpenAI live without Jim's separate approval; weaken a protected check; push, publish or commit.

## Acceptance and evidence

- Protected checks: R1-R4 and R6 suites; existing live accounting suites unmodified.
- Combined validation: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`, plus the step 03 timing.
- Evidence per step in `evidence:`; step 03 writes `results.md`.

## Escalate when

A width in the ramp causes errors that are not cost (the plan then backs down by itself) and even width 2 errors; a guard cannot be made safe without raising a cap; the measured gain is below the threshold and Jim should decide whether to keep the change; an OpenAI live run is wanted. Bring the specific decision.

## Exceptions and retirements

None expected. A measured gain below 25% is a finding to report, not a retired requirement.
