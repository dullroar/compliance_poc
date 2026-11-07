---
id: 01-pin-mcp-runtime
status: done
depends_on: []
touches:
  - requirements.txt
  - requirements-mcp.lock
  - tests/test_mcp_dependency_compat.py
lane: dependency-runtime
gate: .venv/bin/python -m pip check && .venv/bin/python -m unittest tests.test_mcp_dependency_compat -v
requirements: [R1, R4]
evidence: >-
  2026-11-06: Python 3.12.3, mcp 2.0.0 and anyio 4.13.0 selected; installed MCP
  metadata requires anyio >=4.9 on Python 3.12, and the bounded async SDK probe and
  transport API checks pass. The MCP transitive resolution is pinned in requirements-mcp.lock.
  `.venv/bin/python -m pip check && .venv/bin/python -m unittest tests.test_mcp_dependency_compat -v`
  passed (2 tests). A new environment was created with `python3 -m venv /tmp/fix-mcp-verified-venv`;
  `/tmp/fix-mcp-verified-venv/bin/python -m pip install --no-index --find-links /tmp/fix-mcp-wheelhouse -c requirements-mcp.lock 'mcp==2.0.0' 'anyio==4.13.0'`
  passed using wheels recovered from the local pip HTTP cache, then
  `/tmp/fix-mcp-verified-venv/bin/python -m pip check && /tmp/fix-mcp-verified-venv/bin/python -m unittest tests.test_mcp_dependency_compat -v`
  passed (2 tests). An additional full-application requirements dry run could not resolve
  json-rpc from that wheelhouse; the clean MCP dependency gate above does not install the
  unrelated A2A stack.
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
