"""Stdio MCP client.

Used for local Atlassian MCP:
- command: mcp-atlassian
- transport: stdio

This matches your local MCP configuration.
"""

from __future__ import annotations

import os
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from ea_agent.infrastructure.mcp.base import normalize_mcp_result


class StdioMcpClient:
    """Thin wrapper around a stdio MCP server."""

    def __init__(
        self,
        command: str,
        args: list[str],
        env: dict[str, str] | None = None,
    ) -> None:
        self._command = command
        self._args = args
        self._env = env or {}

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        merged_env = dict(os.environ)
        merged_env.update(self._env)

        params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=merged_env,
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return normalize_mcp_result(result)

    async def list_tools(self) -> list[str]:
        merged_env = dict(os.environ)
        merged_env.update(self._env)

        params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=merged_env,
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [tool.name for tool in tools.tools]