"""Skills execute. They call MCP adapters; they contain NO business reasoning
and stay reusable across future agents (PROJECT_CONTEXT §19-20)."""
from __future__ import annotations

from typing import Any


class McpResearchSkill:
    """Implements ResearchSkillPort via Jira/Confluence/ARCO MCP servers."""

    def __init__(self, jira_mcp, confluence_mcp, arco_mcp):
        self._jira = jira_mcp
        self._confluence = confluence_mcp
        self._arco = arco_mcp

    async def search_jira_hierarchy(self, sr_id: str) -> dict[str, Any]:
        # SR -> PACK -> (FEAT) -> BUS -> ACC + AUX; ignore Closed/Duplicate.
        return await self._jira.call("get_issue_hierarchy", {"key": sr_id})

    async def search_confluence(self, query: str, spaces: list[str]) -> dict[str, Any]:
        return await self._confluence.call(
            "search", {"query": query, "spaces": spaces})

    async def search_arco(self, query: str) -> dict[str, Any]:
        return await self._arco.call("search", {"query": query})


class ConfluencePublishSkill:
    def __init__(self, confluence_mcp):
        self._confluence = confluence_mcp

    async def publish_confluence(self, space: str, title: str, body: str) -> str:
        res = await self._confluence.call(
            "create_page", {"space": space, "title": title, "body": body})
        return res.get("url", "")