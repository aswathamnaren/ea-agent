"""Real MCP client adapter (Infrastructure layer).

Connects to MCP servers over streamable HTTP and exposes a simple .call()
interface used by the research skill. Skills execute; no reasoning here.
"""
from __future__ import annotations

from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class McpClient:
    """Thin wrapper around one MCP server (e.g. Jira, Confluence)."""

    def __init__(self, server_url: str):
        self._url = server_url

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Open a session, call one tool, return its result."""
        async with streamablehttp_client(self._url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                # MCP returns content blocks; extract text
                return [c.text for c in result.content if hasattr(c, "text")]