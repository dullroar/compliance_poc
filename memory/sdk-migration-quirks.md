---
gist: "Read when: upgrading or testing against the mcp 2.x or a2a-sdk 1.x libraries, or an A2A task fails with an enqueue-order error."
---

# MCP and A2A SDK quirks

- 2026-10-08 — `mcp` 2.x renamed FastMCP to `mcp.server.mcpserver.MCPServer` (`from mcp.server.fastmcp import ...` raises a migration error); the in-process `Client(server_obj)` makes MCP tools testable without a subprocess. The `a2a-sdk` 1.x `DefaultRequestHandlerV2` rejects a `TaskStatusUpdateEvent` unless the executor first enqueues a `Task` (`new_task_from_user_message`); the symptom is a JSON-RPC "Agent should enqueue Task before TaskStatusUpdateEvent" error. The SDK also logs a harmless "EventQueueSource ... cancelled" warning when `asyncio.run` exits.
