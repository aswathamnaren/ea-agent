"""HTTP MCP client.

Used for ARCO MiniBot MCP:
https://chat.daai.ddc.telefonica.de/mcp/
"""

from __future__ import annotations

from os import read
from turtle import write
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from ea_agent.infrastructure.mcp.base import normalize_mcp_result


class HttpMcpClient:
    """Thin wrapper around an HTTP MCP server."""

    def __init__(self, server_url: str) -> None:
        self._server_url = server_url

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        async with streamablehttp_client(self._server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return normalize_mcp_result(result)

    async def list_tools(self) -> list[str]:
        async with streamablehttp_client(self._server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [tool.name for tool in tools.tools]