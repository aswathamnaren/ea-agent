"""Enterprise research skill.

This skill coordinates:
- Jira for SR / BUS / ACC / AUX requirements
- Confluence for live architecture and component search
- ARCO MiniBot for historical SADs and existing solution patterns

The agent decides what is needed. This skill executes the retrieval.
"""

from __future__ import annotations
from ea_agent.infrastructure.research_logger import (
    log_research_call,
    log_research_result,
)
from typing import Any
from ea_agent.infrastructure.mcp.errors import looks_like_mcp_error
from ea_agent.infrastructure.mcp.serialization import make_json_safe
from ea_agent.config.settings import McpSettings


class EnterpriseResearchSkill:
    """Research execution skill backed by Atlassian MCP and ARCO MCP."""

    def __init__(
        self,
        atlassian_mcp,
        arco_mcp,
        settings: McpSettings,
    ) -> None:
        self._atlassian = atlassian_mcp
        self._arco = arco_mcp
        self._settings = settings

    async def search_jira_hierarchy(self, sr_id: str) -> dict[str, Any]:
        """Fetch Jira data for SAD generation.

        Initial version:
        - fetch SR issue
        - run JQL search for related child tickets

        Later we can improve this using exact Jira hierarchy fields once
        your MCP tool schema is confirmed.
        """
        issue_args = {"issueKey": sr_id}

        log_research_call(
            source="jira",
            tool=self._settings.jira_get_issue_tool,
            arguments=issue_args,
        )

        sr = await self._atlassian.call(
            self._settings.jira_get_issue_tool,
            {"issue_key": sr_id},
        )
        log_research_result("jira.get_issue", sr)
        
        if looks_like_mcp_error(sr):
            raise RuntimeError(f"Jira get issue MCP call failed: {sr}")

        jql = (
            f'issuekey = "{sr_id}" '
            f'OR parent = "{sr_id}" '
            f'OR issueFunction in linkedIssuesOf("issuekey = {sr_id}")'
        )
        search_args = {"jql": jql}
        
        log_research_call(
                    source="jira",
                    tool=self._settings.jira_search_tool,
                    arguments=search_args,
                )

        related = await self._atlassian.call(
            self._settings.jira_search_tool,
            {"jql": jql},
        )
        log_research_result("jira.search", related)
        
        if looks_like_mcp_error(related):
            raise RuntimeError(f"Jira search MCP call failed: {related}")

        return {
            "sr_id": sr_id,
            "sr": sr,
            "jql": jql,
            "related": related,
            "source": "jira",
        }

    async def search_confluence(
        self,
        query: str,
        spaces: list[str],
    ) -> dict[str, Any]:
        """Search live Confluence knowledge."""

        search_args = {
            "query": query,
        }

        log_research_call(
            source="confluence",
            tool=self._settings.confluence_search_tool,
            arguments=search_args,
        )

        search_results = await self._atlassian.call(
            self._settings.confluence_search_tool,
            search_args,
        )

        log_research_result("confluence.search", search_results)
        
        if looks_like_mcp_error(search_results):
            raise RuntimeError(f"Confluence search MCP call failed: {search_results}")

        parent_page_results: list[Any] = []

        for parent in self._settings.confluence_parent_pages_list:
            child_args = {"pageUrl": parent}

            log_research_call(
                source="confluence",
                tool=self._settings.confluence_get_children_tool,
                arguments=child_args,
            )

            try:
                children = await self._atlassian.call(
                    self._settings.confluence_get_children_tool,
                    child_args,
                )

                log_research_result(
                    source=f"confluence.children.{parent}",
                    result=children,
                )
                
                if looks_like_mcp_error(children):
                    raise RuntimeError(f"Confluence get children MCP call failed: {children}")

                parent_page_results.append(
                    {
                        "parent": parent,
                        "children": children,
                    }
                )
            except Exception as exc:
                parent_page_results.append(
                    {
                        "parent": parent,
                        "error": str(exc),
                    }
                )

        return {
            "query": query,
            "spaces": spaces,
            "search_results": search_results,
            "parent_page_results": parent_page_results,
            "source": "confluence",
        }

    async def search_arco(self, query: str) -> dict[str, Any]:
        """Search ARCO MiniBot enterprise RAG."""

        if self._arco is None:
            return {
                "query": query,
                "results": [],
                "source": "arco",
                "enabled": False,
            }

        args = {"question": query}

        log_research_call(
            source="arco",
            tool=self._settings.arco_search_tool,
            arguments=args,
        )

        result = await self._arco.call(
            self._settings.arco_search_tool,
            args,
        )
        result = make_json_safe(result)
        log_research_result("arco.search", result)

        if looks_like_mcp_error(result):
            raise RuntimeError(f"ARCO search MCP call failed: {result}")

        return {
            "query": query,
            "results": result,
            "source": "arco",
            "enabled": True,
        }

    async def search_existing_solutions(self, sr_id: str, summary: str = "") -> dict[str, Any]:
        """Ask ARCO for reusable solution patterns and previous SADs."""
        query = (
            f"Find existing solution architecture documents, SADs, reusable "
            f"patterns, integration designs, impacted systems, API decisions, "
            f"and architecture rules similar to SR {sr_id}. Context: {summary}"
        )

        return await self.search_arco(query)