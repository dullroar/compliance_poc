---
id: 02-async-server-adapter
status: done
depends_on: []
touches:
  - compliance_common/mcp_server.py
  - tests/test_mcp_server_runtime.py
lane: server-runtime
gate: timeout 15s .venv/bin/python -m unittest tests.test_mcp_server_runtime -v
requirements: [R2, R4]
evidence: >-
  2026-11-06: `timeout 15s .venv/bin/python -m unittest tests.test_mcp_server_runtime -v`
  passed (2 tests, 0.077s) using Python 3.12.3, mcp 2.0.0 and anyio 4.13.0.
  A synchronous test evaluator received the canonical case exactly once; the real YBS
  decision ID and classification matched direct evaluation. Both calls and client exits
  completed while anyio.to_thread.run_sync was patched to fail, so the test detects
  reintroduction of the worker bridge. The evaluators remain local and no network or
  subprocess calls were found in their rules or server modules.
---

# Remove the synchronous worker bridge from evaluator tool execution

Register the generic deterministic-evaluator adapter as an async MCP tool while preserving its direct evaluator call, observability, validation behavior, and result shape.

## Change

- `compliance_common/mcp_server.py`: make the registered tool handler asynchronous and invoke the existing synchronous evaluator directly inside it, avoiding the SDK's automatic AnyIO worker-thread scheduling for sync handlers.
- `tests/test_mcp_server_runtime.py`: add a bounded minimal-server and YBS-server regression test that proves a synchronous evaluator returns through the async adapter and the in-process client exits cleanly.

## Do not change

- The evaluator callable signatures, validation exceptions, decision record, logging fields, tool name, input schema, or authoritative decision behavior.

## Dependencies already satisfied

- None. This step may run in parallel with `01-pin-mcp-runtime` because it changes distinct files and proves the implementation-level scheduling boundary.

## Completion criteria

- The focused test completes before the timeout; it compares direct and MCP decision IDs and classifications.
- A test double confirms the evaluator is still called exactly once with the canonical case.
- The test would hang or fail if the server reintroduces the SDK's synchronous tool worker path.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
