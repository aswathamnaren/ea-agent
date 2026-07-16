"""Ports (interfaces). The Agent depends on these abstractions, never on
concrete infrastructure. Skills execute; the Agent only orchestrates them.
"""
from __future__ import annotations

from typing import Protocol, Any


class ReasonerPort(Protocol):
    """LLM reasoning abstraction (implemented by Bedrock adapter)."""
    async def reason(self, system_prompt: str, user_prompt: str) -> str: ...
    async def reason_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]: ...


class ResearchSkillPort(Protocol):
    """Execution skill for enterprise knowledge retrieval (via MCP)."""
    async def search_jira_hierarchy(self, sr_id: str) -> dict[str, Any]: ...
    async def search_confluence(self, query: str, spaces: list[str]) -> dict[str, Any]: ...
    async def search_arco(self, query: str) -> dict[str, Any]: ...


class DiagramSkillPort(Protocol):
    async def render_plantuml(self, puml: str) -> str: ...  # returns artefact ref/URL


class PublishSkillPort(Protocol):
    async def publish_confluence(self, space: str, title: str, body: str) -> str: ...


class CheckpointRepositoryPort(Protocol):
    """Persistence abstraction — never leaks DynamoDB/Postgres into the app layer."""
    async def save(self, execution_id: str, state: dict[str, Any]) -> None: ...
    async def load(self, execution_id: str) -> dict[str, Any] | None: ...

class PromptProviderPort(Protocol):
    """Abstraction over prompt retrieval (implemented by PromptLoader)."""
    def get(self, name: str) -> str: ...
    def render(self, name: str, **variables: object) -> str: ...