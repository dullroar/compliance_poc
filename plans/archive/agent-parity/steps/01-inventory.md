---
id: 01-inventory
status: done
depends_on: []
touches:
  - plans/agent-parity/inventory.md
lane: serial
gate: python3 scripts/check_plan.py && python3 scripts/check_context.py
requirements: [R1]
evidence: "2026-11-06, Python 3.12.3. Registry set from agents.yaml: hmda, ecoa, hvcre, hpml, trid, fzd, ybs, vmi, auditor, narrative (10). Baseline: python3 -m unittest discover -s tests -> 306 tests OK, 3 skipped (opt-in live). Gate python3 scripts/check_plan.py && python3 scripts/check_context.py -> all ok. Matrix review: a script confirmed the 10 matrix columns equal the registry keys and all 11 capability rows have 10 cells; every cell cites a proof key, a gap id G1-G12, or an N/A reason; G9/G10 are suspected defects left explicit until reproduced. Only plans/agent-parity/inventory.md was created."
---

# Inventory YBS capabilities and every registered role

## Change

- Create `plans/agent-parity/inventory.md` with YBS reference evidence and a matrix for every `agents.yaml` entry against R1 capabilities. Cite implementation and existing tests, distinguish verified from inferred, and document role-specific not-applicable cases. Identify concrete gaps, affected paths, proposed tests and dispositions; unknowns must remain explicit until verified later.
- Include runtime contract coverage of canonical mapping, model and seeded modes, MCP stdio, cards/tasks, grounding and provenance, plus batch ordering and failure isolation. Identify differences in auditor and narrator behavior without treating them as defects by default.

## Do not change

Runtime, domain decisions, registry behavior, protected checks or documentation outside the inventory.

## Dependencies already satisfied

None.

## Completion criteria

Every registered role and R1 capability appears in the matrix, with a reference or an explicit unknown/gap. Proposed repairs remain inside delegated scope or are escalated. The gate passes; it validates plan/context structure, while matrix completeness is reviewed against the registry.

## Record

Record the gate, date, registry set and matrix review in `evidence:`; mark `done` only when the criteria pass.
