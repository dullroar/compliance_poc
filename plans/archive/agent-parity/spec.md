---
gist: "Read when: bringing remaining compliance agents and orchestration to applicable YBS runtime and A2A parity."
---

# Agent and orchestration parity with YBS - specification and execution agreement

Status: complete (approved by Jim Lehmer, 2026-11-06; verified 2026-11-06)

See [goal.md](goal.md) for the assistant-agnostic execution prompt and protocol.

## Goal and exclusions

Bring the rest of the repository up to the applicable runtime, deterministic evaluation, MCP, A2A, provenance and narrative-safety practices demonstrated by YBS. First inventory actual behavior and evidence; much is already shared, including A2A and tool-backed domain execution. Repair verified gaps and stale operator documentation, then prove integration across the registry. Preserve meaningful differences among domain evaluators, the auditor, and the optional report narrator. This is not a regulatory rule rewrite, model-provider expansion, production deployment, new protocol, or demand for identical domain outputs.

## Requirements

### R1. Trace applicable capabilities across every registered role

- Basis: documented ([registry-driven A2A](../../../docs/design/registry-driven-a2a-orchestration.md), [authority boundary](../../../docs/design/code-decides-agents-narrate.md)); inferred: compare each actual role to the current YBS reference instead of assuming missing features.
- Example: the inventory lists each configured domain, auditor and narrative role against registry/card and A2A task behavior, canonical input/tool authority, MCP transport, tool modes, provenance, guards and failure handling; each cell has a file/test reference and status: verified, gap, or not applicable with reason.
- Acceptance check: the matrix in `plans/agent-parity/inventory.md` covers every current `agents.yaml` entry, identifies YBS baseline evidence and cites runnable or inspectable proof, including exceptions for auditor and narrative. Unknowns are not labeled verified.

### R2. Domain agents satisfy the applicable YBS runtime contracts

- Basis: documented ([README deterministic evaluators](../../../README.md), [authority boundary](../../../docs/design/code-decides-agents-narrate.md)); inferred: equivalent integration guarantees apply across domains while preserving domain decisions.
- Example: for each registered domain, a synthetic canonical case produces the same decision ID and classification via direct evaluation, MCP stdio and an A2A agent task with an offline fake narrator; canonical facts cannot be replaced by model-supplied arguments and guard/decision metadata survive the transport.
- Acceptance check: new offline, table-driven contract tests cover every configured evaluator-backed domain, including missing canonical input, model and seeded modes where applicable, argument pinning and guard/fallback behavior; existing evaluator fixtures remain unchanged. Test bounded subprocess cleanup and verify the appropriate per-domain decision fields instead of assuming identical schemas.

### R3. Orchestration and role-specific contracts remain observable

- Basis: documented ([registry-driven A2A](../../../docs/design/registry-driven-a2a-orchestration.md), [raw and parsed results](../../../docs/design/raw-and-parsed-results-retained.md)).
- Example: cards and A2A tasks cover every registered role; independent domain failures are visible while other results survive; auditor runs after domains and optional narrative follows; role-specific results retain appropriate raw, parsed and failure evidence.
- Acceptance check: offline A2A and batch integration tests cover all configured roles, ordering, selection, concurrency, and failure isolation, without requiring live model services. The narrator is not forced to emit domain decisions or MCP results when not applicable.

### R4. Evidence and operator guidance describe the actual system

- Basis: documented ([context ownership](../../../AGENTS.md)); inferred: stale YBS-pilot-only guidance and registry counts may conceal actual capabilities.
- Example: the inventory records a disposition and test evidence for each gap; the README and relevant canonical design documents accurately describe shared behavior and exceptions without claiming compliance approval.
- Acceptance check: no inventory item remains unknown or unresolved; `python3 -m unittest discover -s tests -v`, `python3 scripts/check_context.py`, and `python3 scripts/check_plan.py` pass.

## Constraints and assumptions

- The current registry includes eight domain agents plus auditor and narrative; rederive the set from `agents.yaml` during execution rather than hard-coding it. Applicability of a YBS capability to each role is inferred and must be justified in the inventory, not forced mechanically.
- Existing domain rules, regulatory interpretations, pack thresholds, case schemas, deterministic outcomes, and their domain-specific classification fields are authoritative; no regulatory change is delegated. Synthetic fixtures and fake model clients only. Existing direct/in-process/stdio assertions are protected.
- YBS is the runtime reference, not proof that every detail is suitable for all roles. If a difference requires a new regulatory, schema, or product decision, escalate with evidence. If a fixture cannot exercise a domain, record the missing fixture and add a synthetic one without changing business rules.

## Domain challenge

- *Suspicious - explain it:* Shared infrastructure can give a false impression of complete per-domain coverage. Resolution (inferred): enumerate registry roles and prove behavior per role with runnable contracts.
- *Suspicious - explain it:* Narrative and auditor roles differ from domain agents. Resolution (documented in the A2A design): test their actual role-specific contracts and document not-applicable cells; do not invent domain parity.
- *Contradicts a confirmed rule:* Copying YBS thresholds or classifications to another domain would alter deterministic authority. Resolution: preserve each domain's contracts and fixtures; escalate interpretation changes.

## Delegated authority

- Once approved, the executor MAY inventory and edit the shared runtime, MCP adapters/servers, orchestrator, registry configuration, focused tests/synthetic fixtures, and directly related README/design documentation as needed to close demonstrated integration gaps. Refactor only within this goal; retain existing interfaces and deterministic outputs.
- The executor MUST NOT change regulatory rules, thresholds, domain input/output schemas, source packs, prompt interpretations, protected tests, default provider/model, external systems, real data, or live model services; push, publish or commit. A required change outside this boundary needs a decision.

## Acceptance and evidence

- Protected checks: existing evaluator tests and fixtures, deterministic direct/MCP/A2A parity, pinned canonical inputs, grounding/guard behavior, role-appropriate A2A results, ordering and failure isolation, offline full suite, context and plan validation. Do not weaken or remove checks to pass.
- Combined validation: `python3 -m unittest discover -s tests -v && python3 scripts/check_context.py && python3 scripts/check_plan.py`.
- Every completed step records date, exact commands and outcomes in `evidence:`. The inventory records evidence and disposition for every role/capability cell and gap.

## Escalate when

A verified gap requires a regulatory interpretation, changed evaluator decision/schema, new provider or live data; role applicability is contradictory; a protected check cannot pass; or required work exceeds delegated paths. Bring the concrete discrepancy and decision needed; leave the plan incomplete.

## Exceptions and retirements

Distinguish an incorrect test, outdated documentation, withdrawn requirement and approved tolerated violation. Do not retire a check as a workaround; record any owner-approved tolerated violation in [exception-record.md](exception-record.md).
