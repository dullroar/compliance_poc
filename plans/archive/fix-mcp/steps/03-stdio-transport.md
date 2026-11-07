---
id: 03-stdio-transport
status: done
depends_on: [01-pin-mcp-runtime, 02-async-server-adapter]
touches:
  - compliance_common/mcp_client.py
  - tests/test_mcp_client_stdio.py
lane: client-transport
gate: timeout 20s .venv/bin/python -m unittest tests.test_mcp_client_stdio -v
requirements: [R1, R3, R4]
evidence: >-
  2026-11-06: `timeout 20s .venv/bin/python -m unittest tests.test_mcp_client_stdio -v`
  passed outside the execution sandbox (1 test, 1.336s), with Python 3.12.3,
  mcp 2.0.0 and anyio 4.13.0. Real YBS subprocesses provided tool discovery and
  a wire invocation; their process handles had exited on return, and the decision ID
  and classification matched direct evaluation. The same gate timed out in the
  sandbox (exit 124) before discovery. The local reproduction
  `timeout 5s .venv/bin/python -c 'import anyio; print(anyio.run(anyio.to_thread.run_sync, lambda: 1), flush=True)'`
  also timed out there but printed 1 and exited 0 outside it; the SDK stdio server
  uses AnyIO file operations. No network call was used for either check.
---

# Use the supported stdio transport and prove child-process lifecycle

Adapt the MCP client helper to turn `StdioServerParameters` into the exact async transport required by the selected SDK, then test the real YBS server as a subprocess.

## Change

- `compliance_common/mcp_client.py`: retain `stdio_target()` as launch configuration but construct and pass the SDK-supported stdio transport to `Client`; preserve existing decoding and error handling.
- `tests/test_mcp_client_stdio.py`: launch the YBS server through the helper, list its tool specification, call `ybs_evaluate` with a synthetic canonical case, compare its decision ID with direct evaluation, and assert bounded clean shutdown.

## Do not change

- The server executable command, evaluator rules, protocol payload, or public `call_tool()` result contract. Do not substitute an in-process server for this test.

## Dependencies already satisfied

- `01-pin-mcp-runtime` identifies the SDK API and supported dependency set used by this transport adapter.
- `02-async-server-adapter` removes the worker-bridge stall from the real server used by this step's subprocess test.

## Completion criteria

- No `TypeError` occurs from treating `StdioServerParameters` as a transport.
- The subprocess test exits before its timeout and leaves no child process behind.
- The test proves both tool discovery and a real wire call; it does not accept a mocked transport.

## Record

Set `status: done` and fill `evidence:` with the gate's outcome (command, result, date). Note any missing verification instead of omitting it.
