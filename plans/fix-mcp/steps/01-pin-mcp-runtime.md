---
id: 01-pin-mcp-runtime
status: pending
depends_on: []
touches:
  - requirements.txt
  - requirements-mcp.lock
  - tests/test_mcp_dependency_compat.py
lane: dependency-runtime
gate: .venv/bin/python -m pip check && .venv/bin/python -m unittest tests.test_mcp_dependency_compat -v
requirements: [R1, R4]
evidence: ""
---

# Select and lock the supported MCP and AnyIO runtime pair

Determine a compatible, reproducible MCP SDK environment rather than relying on the current open-ended `mcp>=2.0` constraint.

## Change

- `requirements.txt`: replace the broad MCP lower bound with an explicit supported constraint; add any required direct constraint for AnyIO.
- `requirements-mcp.lock`: record the fully resolved MCP-related package set and Python version used to validate it, if a lock artifact is needed by the repository's installation workflow.
- `tests/test_mcp_dependency_compat.py`: add a focused offline compatibility probe that asserts the selected APIs import and a bounded MCP lifecycle probe has the expected behavior.

## Do not change

- Evaluator, tool, prompt, or contract semantics; do not select versions merely because installation succeeds.

## Dependencies already satisfied

- None. This step may run in parallel with `02-async-server-adapter` because it does not edit the server adapter or its test module.

## Completion criteria

- The chosen versions and their rationale are recorded in the step evidence.
- A clean resolved environment passes `pip check` and the focused compatibility probe without network access during the test.
- The compatibility test fails on an unsupported API shape instead of silently accepting any installed SDK version.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, selected versions, result, date). Note any missing verification instead of omitting it.
