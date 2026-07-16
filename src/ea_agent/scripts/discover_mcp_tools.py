"""Discover MCP tool names.

Run:
    python scripts/discover_mcp_tools.py

This helps confirm the actual tool names exposed by:
- mcp-atlassian stdio server
- ARCO MiniBot HTTP MCP server
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from ea_agent.config.settings import get_settings
from ea_agent.infrastructure.mcp.http_client import HttpMcpClient
from ea_agent.infrastructure.mcp.stdio_client import StdioMcpClient


async def main() -> None:
    settings = get_settings()

    print("\n=== Atlassian MCP tools ===")
    atlassian_env = {
        "CONFLUENCE_URL": os.getenv("CONFLUENCE_URL", ""),
        "CONFLUENCE_PERSONAL_TOKEN": os.getenv("CONFLUENCE_PERSONAL_TOKEN", ""),
        "CONFLUENCE_SSL_VERIFY": os.getenv("CONFLUENCE_SSL_VERIFY", "false"),
        "JIRA_URL": os.getenv("JIRA_URL", ""),
        "JIRA_PERSONAL_TOKEN": os.getenv("JIRA_PERSONAL_TOKEN", ""),
        "JIRA_SSL_VERIFY": os.getenv("JIRA_SSL_VERIFY", "false"),
        "TOOLSETS": os.getenv("TOOLSETS", "all"),
    }

    atlassian = StdioMcpClient(
        command=settings.mcp.atlassian_command,
        args=settings.mcp.atlassian_args_list,
        env=atlassian_env,
    )

    try:
        tools = await atlassian.list_tools()
        for tool in tools:
            print(f"- {tool}")
    except Exception as exc:
        print(f"Failed to list Atlassian tools: {exc}")

    print("\n=== ARCO MiniBot MCP tools ===")
    arco = HttpMcpClient(settings.mcp.arco_url)

    try:
        tools = await arco.list_tools()
        for tool in tools:
            print(f"- {tool}")
    except Exception as exc:
        print(f"Failed to list ARCO tools: {exc}")


if __name__ == "__main__":
    asyncio.run(main())