---
gist: "Read when: repairing the MCP client/server lifecycle regression and its test coverage."
---

# MCP lifecycle repair - specification and execution agreement

Status: approved (by Jim Lehmer, 2026-11-06)

## Goal and exclusions

Repair the local MCP execution path so deterministic evaluator calls complete and their clients shut down cleanly under a reproducible SDK environment. The diagnosed failure is not an evaluator decision failure: a synchronous registered MCP tool reaches the installed SDK's `anyio.to_thread.run_sync()` path, which stalls in this runtime. The current stdio helper also passes configuration where the installed MCP client requires a transport. This work does **not** change evaluator rules, packs, prompts, decisions, classifications, remote transports, or model-provider behavior.

## Requirements

### R1. The MCP SDK environment is reproducible and explicitly supported

- Basis: documented ([agent validation rules](../../AGENTS.md)) and observed in the local diagnosis (`mcp==2.0.0`, `anyio==4.13.0`); exact compatible versions remain to be confirmed by the step gate.
- Example: a fresh environment resolves the documented MCP and AnyIO constraints, imports them, and passes dependency consistency checks.
- Acceptance check: the dependency compatibility gate in step `01` passes in a recreated environment; its evidence records the selected versions.

### R2. A deterministic evaluator call cannot block on MCP's synchronous worker bridge

- Basis: observed local reproduction: direct `evaluate_ybs()` completes, while a minimal synchronous MCP tool and `anyio.to_thread.run_sync(lambda: 1)` stall; an equivalent async tool completes.
- Example: calling `ybs_evaluate` through an in-process MCP client returns the same decision ID as direct evaluation and exits within the bounded test duration.
- Acceptance check: the focused server-runtime regression test in step `02` passes with a timeout guard.

### R3. The stdio client uses the SDK's supported transport boundary

- Basis: observed local API behavior: passing `StdioServerParameters` directly to `Client` raises `TypeError`; the parameters are server-launch configuration, not a transport.
- Example: `stdio_target("ybs")` is converted to the SDK stdio transport, launches `python -m compliance_mcp.ybs.server`, calls `ybs_evaluate`, and closes the child process.
- Acceptance check: the bounded real-subprocess conformance test in step `03` passes.

### R4. Contract tests distinguish in-process behavior from stdio wire behavior

- Basis: documented ([MCP client helper](../../compliance_common/mcp_client.py)) and inferred (separate transport paths need separate lifecycle assertions).
- Example: an in-process test proves evaluator parity without wire assumptions, while a subprocess test proves stdio framing, invocation, and shutdown.
- Acceptance check: the repaired shared contract test plus the full offline suite pass in step `04`.

## Constraints and assumptions

- The selected dependency pair must be supported by its published package metadata and demonstrated by the focused gates; do not assume that a broad lower bound remains API-compatible.
- `evaluate_*` functions remain the authority and must keep their inputs, output records, and exception semantics unchanged. The server adapter may change only how it schedules the call.
- A direct asynchronous wrapper is acceptable only while the evaluator is bounded, local, and CPU-light. If an evaluator becomes blocking I/O or materially expensive, return for an explicit execution-model decision rather than silently moving it back to an unsafe worker bridge.
- All subprocess tests use only synthetic fixture data and bounded timeouts. They must clean up the spawned process.

## Domain challenge

- *Suspicious - explain it:* A passing async wrapper could hide a different stdio lifecycle defect. Resolution: retain a separate real-subprocess test in `03`; confirmed by its recorded gate.
- *Suspicious - explain it:* Pinning versions alone could make a broken sync-tool path appear stable on one machine. Resolution: `02` permanently tests the no-worker-bridge server adapter, not merely a particular scheduling accident.
- *Contradicts a confirmed rule:* Altering evaluator output to make serialization smaller or easier would violate the deterministic-authority boundary. Resolution: excluded; parity assertions compare the existing decision ID and classification.

## Delegated authority

- The executor MAY: edit dependency constraints, MCP client/server adapters, focused MCP tests, the existing YBS MCP contract test, and documentation directly related to the selected SDK behavior; create a lock or constraints artifact if needed for reproducibility.
- The executor MUST NOT: change deterministic evaluator/pack/prompt logic; weaken, skip, or delete protected evaluator or contract assertions; make live network calls; change provider behavior; push, publish, or change remotes.

## Acceptance and evidence

- Protected checks: direct-versus-MCP decision parity, bounded client shutdown, real stdio subprocess invocation and cleanup, the existing evaluator fixtures, and the full offline test suite.
- Combined validation after parallel steps merge: `.venv/bin/python -m unittest discover -s tests -v && .venv/bin/python scripts/check_context.py && .venv/bin/python scripts/check_plan.py`.
- Each completed step records its date, exact command, selected dependency versions where applicable, and result in `evidence:`. A timeout is a failure signal, not a passing result.

## Escalate when

No published compatible MCP/AnyIO pair can pass the bounded probes; the clean-environment gate cannot be completed with locally available distributions under the no-network constraint; the selected SDK requires a client/server API change outside the named adapters; a deterministic evaluator is no longer safe to execute directly in the async wrapper; a protected parity check changes; or a subprocess cannot be reliably cleaned up. Bring back the failing command, versions, and the smallest reproduction.

## Exceptions and retirements

Do not retire the failed test as a workaround. If a test is incorrect, documentation is outdated, a requirement is withdrawn, or a violation is tolerated, record the applicable outcome under this plan using the repository exception format.
