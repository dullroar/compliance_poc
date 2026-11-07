"""Bounded checks of the supported MCP SDK interface and async lifecycle."""
import subprocess
import sys
import unittest
from importlib.metadata import version

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.mcpserver import MCPServer


class MCPDependencyCompatibilityTests(unittest.TestCase):
    def test_supported_versions_and_transport_shape(self):
        self.assertEqual(version("mcp"), "2.0.0")
        self.assertEqual(version("anyio"), "4.13.0")
        self.assertTrue(callable(Client))
        self.assertTrue(callable(MCPServer.add_tool))
        transport = stdio_client(StdioServerParameters(command=sys.executable))
        self.assertTrue(callable(getattr(transport, "__aenter__", None)))
        self.assertTrue(callable(getattr(transport, "__aexit__", None)))
        self.assertIsInstance(Client(transport), Client)

    def test_async_tool_lifecycle_is_bounded(self):
        probe = '''
import asyncio, json
from mcp import Client
from mcp.server.mcpserver import MCPServer
server = MCPServer("dependency-probe")
async def ping(value: int) -> dict:
    return {"value": value}
server.add_tool(ping, name="ping")
async def main():
    async with Client(server) as client:
        listing = await client.list_tools()
        assert [tool.name for tool in listing.tools] == ["ping"]
        result = await client.call_tool("ping", {"value": 7})
        assert not result.is_error
        assert json.loads(result.content[0].text) == {"value": 7}
asyncio.run(main())
'''
        completed = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
