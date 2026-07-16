"""Strongly-typed application settings (Configuration Management, PROJECT_CONTEXT §50).

All runtime configuration originates from environment variables, a local .env file
(development only), or Kubernetes ConfigMaps / Secrets in deployed environments.
Application code consumes configuration ONLY through these typed Settings objects —
never via os.environ directly and never hardcoded.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# 👇 ADD: load .env into the environment BEFORE any Settings class is created.
# Anchored to the project root so it works regardless of where you run from.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]   # config → ea_agent → src → ea-agent/
load_dotenv(_PROJECT_ROOT / ".env")


class BedrockSettings(BaseSettings):
    """AWS Bedrock reasoning model configuration (Infrastructure layer)."""
    model_config = SettingsConfigDict(env_prefix="BEDROCK_", extra="ignore")
    profile: str | None = Field(
        default=None,
        description="AWS named profile (e.g. 'saml') for local dev.",
    )
    model_id: str = Field(
        default="anthropic.claude-sonnet-4-5-v1:0",
        description="Bedrock model identifier used by the reasoner.",
    )
    region: str = Field(default="eu-central-1", description="AWS region for Bedrock.")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, gt=0, le=200_000)


class DynamoDBSettings(BaseSettings):
    """DynamoDB checkpoint persistence."""

    model_config = SettingsConfigDict(env_prefix="DYNAMODB_", extra="ignore")

    table_name: str = "ea-agent-checkpoints"
    region: str = "eu-central-1"
    endpoint_url: str | None = None


class McpSettings(BaseSettings):
    """MCP server configuration for enterprise knowledge retrieval."""

    model_config = SettingsConfigDict(env_prefix="MCP_", extra="ignore")

    use_real_clients: bool = Field(
        default=False,
        description="Use real MCP clients instead of fake smoke-test skills.",
    )

    # Atlassian MCP - stdio
    atlassian_transport: Literal["stdio", "http"] = "stdio"
    atlassian_command: str = "mcp-atlassian"
    atlassian_args: str = (
        "--no-confluence-ssl-verify,"
        "--no-jira-ssl-verify,"
        "--transport,"
        "stdio"
    )

    # ARCO MiniBot MCP - HTTP
    arco_transport: Literal["http", "stdio"] = "http"
    arco_url: str = ""

    # Jira tool names
    jira_get_issue_tool: str = "jira_get_issue"
    jira_search_tool: str = "jira_search"

    # Confluence tool names
    confluence_search_tool: str = "confluence_search"
    confluence_get_page_tool: str = "confluence_get_page"
    confluence_get_children_tool: str = "confluence_get_page_children"

    # ARCO tool name
    arco_search_tool: str = "search"

    # Confluence knowledge scope
    confluence_parent_page_urls: str = ""
    confluence_spaces: str = "ARCH,RAITT"

    @property
    def atlassian_args_list(self) -> list:
        return [x.strip() for x in self.atlassian_args.split(",") if x.strip()]

    @property
    def confluence_parent_pages_list(self) -> list:
        return [
            x.strip()
            for x in self.confluence_parent_page_urls.split(",")
            if x.strip()
        ]

    @property
    def confluence_spaces_list(self) -> list:
        return [
            x.strip()
            for x in self.confluence_spaces.split(",")
            if x.strip()
        ]


class AgentSettings(BaseSettings):
    """Agent reasoning behaviour."""

    model_config = SettingsConfigDict(env_prefix="AGENT_", extra="ignore")

    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)

    prompts_dir: Path = Field(
        default=Path(__file__).resolve().parents[1] / "prompts",
        description="Directory holding externalised prompt Markdown files.",
    )

    @field_validator("prompts_dir")
    @classmethod
    def _prompts_dir_exists(cls, v: Path) -> Path:
        if not v.is_dir():
            raise ValueError(f"Prompts directory does not exist: {v}")
        return v


class Settings(BaseSettings):
    """Root settings object. Composes all sub-settings.

    Loads from environment variables and, in development, from a .env file.
    In Kubernetes, values are injected via ConfigMaps (non-secret) and
    Secrets (credentials) as environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Structured logging level (§51).",
    )

    bedrock: BedrockSettings = Field(default_factory=BedrockSettings)
    dynamodb: DynamoDBSettings = Field(default_factory=DynamoDBSettings)
    mcp: McpSettings = Field(default_factory=McpSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, process-wide Settings instance.

    Use dependency injection to pass this into infrastructure components rather
    than importing it deep inside business logic.
    """
    return Settings()