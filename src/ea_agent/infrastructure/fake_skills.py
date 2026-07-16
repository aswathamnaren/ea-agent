"""Fake skills for local smoke-testing WITHOUT real MCP. NOT for production."""
from __future__ import annotations

from typing import Any


class FakeResearchSkill:
    async def search_jira_hierarchy(self, sr_id: str) -> dict[str, Any]:
        return {"sr": {"key": sr_id, "summary": "Sample SR"},
                "bus": [{"key": "BUS-1001", "summary": "Agent can port a number"}],
                "acc": [{"key": "ACC-2001", "summary": "System validates port request"}],
                "aux": []}

    async def search_confluence(self, query: str, spaces: list[str]) -> dict[str, Any]:
        return {"pages": [{"title": "Sample Arch Page",
                           "content": "Reference: REST via middleware."}]}

    async def search_arco(self, query: str) -> dict[str, Any]:
        return {"standards": ["TMF 652 Number Portability"]}


class FakePublishSkill:
    async def publish_confluence(self, space: str, title: str, body: str) -> str:
        print(f"[FAKE PUBLISH] '{title}' -> {space} ({len(body)} chars)")
        return f"https://confluence.example.com/{space}/{title.replace(' ', '+')}"