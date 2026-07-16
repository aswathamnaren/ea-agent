"""Composition root + interrupt/resume driver."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from ea_agent.application.nodes import Nodes
from ea_agent.application.reasoning import ReasoningEngine
from ea_agent.application.workflow import build_agent
from ea_agent.config import settings
from ea_agent.config.settings import get_settings
from ea_agent.infrastructure.bedrock_reasoner import BedrockReasoner
from ea_agent.infrastructure.prompt_loader import PromptLoader
from ea_agent.infrastructure.fake_skills import FakeResearchSkill, FakePublishSkill

logger = logging.getLogger("ea_agent")


def _build_agent():
    settings = get_settings()
    
    print(f"DEBUG MCP_USE_REAL_CLIENTS = {settings.mcp.use_real_clients}")
    print(f"DEBUG MCP_ATLASSIAN_COMMAND = {settings.mcp.atlassian_command}")
    print(f"DEBUG MCP_ARCO_URL = {settings.mcp.arco_url}")

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    profile = settings.bedrock.profile if not settings.is_production else None
    reasoner = BedrockReasoner(model_id=settings.bedrock.model_id,
                               region=settings.bedrock.region, profile=profile)
    prompts = PromptLoader(settings.agent.prompts_dir)

    if settings.mcp.use_real_clients:
        from ea_agent.infrastructure.enterprise_research_skill import EnterpriseResearchSkill
        from ea_agent.infrastructure.mcp.http_client import HttpMcpClient
        from ea_agent.infrastructure.mcp.stdio_client import StdioMcpClient

        atlassian_env = {
            "CONFLUENCE_URL": os.getenv("CONFLUENCE_URL", ""),
            "CONFLUENCE_PERSONAL_TOKEN": os.getenv("CONFLUENCE_PERSONAL_TOKEN", ""),
            "CONFLUENCE_SSL_VERIFY": os.getenv("CONFLUENCE_SSL_VERIFY", "false"),
            "JIRA_URL": os.getenv("JIRA_URL", ""),
            "JIRA_PERSONAL_TOKEN": os.getenv("JIRA_PERSONAL_TOKEN", ""),
            "JIRA_SSL_VERIFY": os.getenv("JIRA_SSL_VERIFY", "false"),
            "TOOLSETS": os.getenv("TOOLSETS", "all"),
        }

        atlassian_mcp = StdioMcpClient(
            command=settings.mcp.atlassian_command,
            args=settings.mcp.atlassian_args_list,
            env=atlassian_env,
        )

        arco_mcp = HttpMcpClient(settings.mcp.arco_url)

        research = EnterpriseResearchSkill(
            atlassian_mcp=atlassian_mcp,
            arco_mcp=arco_mcp,
            settings=settings.mcp,
        )
    else:
        research = FakeResearchSkill()

    publisher = FakePublishSkill()

    
    engine = ReasoningEngine(reasoner, prompts,
                             threshold=settings.agent.confidence_threshold)
    nodes = Nodes(reasoner, research, publisher, engine, prompts)
    return build_agent(nodes, checkpointer=MemorySaver())


async def _stream(agent, payload, config) -> dict:
    last: dict = {}

    async for event in agent.astream(payload, config=config, stream_mode="updates"):
        for node_output in event.values():
            if isinstance(node_output, dict):
                for msg in node_output.get("events", []):
                    print(msg)
        last = event

    return last


def _is_waiting(agent, config) -> bool:
    return bool(agent.get_state(config).next)


def _get_interrupt(agent, config):
    """Return the pending interrupt payload, or None."""
    snap = agent.get_state(config)
    # langgraph exposes interrupts on the snapshot
    interrupts = getattr(snap, "interrupts", None) or []
    if interrupts:
        return interrupts[0].value
    # fallback: look inside pending tasks
    for task in getattr(snap, "tasks", []):
        for intr in getattr(task, "interrupts", []):
            return intr.value
    return None


def _prompt_human(payload: dict) -> dict:
    """Display the interrupt content and collect answers."""
    kind = payload.get("type")

    if kind == "approval_request":
        print("\n=== APPROVAL REQUIRED ===")
        print(f"Document has {len(payload.get('preview', {}))} sections.")
        ans = input("Approve publication? (yes/no): ").strip().lower()
        return {"approved": ans in {"yes", "y", "approve"}}

    # clarification_request
    questions = payload.get("questions", [])
    print("\n=== CLARIFICATION QUESTIONS ===")
    answers: dict[str, str] = {}
    for q in questions:
        print(f"\n[{q['tier']}] {q['id']} — {q['topic']}")
        print(f"  Context: {q['context']}")
        print(f"  ❓ {q['question']}")
        answers[q["id"]] = input("  Your answer: ").strip() or "N/A"
    
    print(f"  Evidence: {q.get('evidence', 'N/A')}")
    print(f"  Context: {q['context']}")
    return answers


async def run() -> None:
    agent = _build_agent()
    thread = {"configurable": {"thread_id": str(uuid.uuid4())},
              "recursion_limit": 50}
    initial = {"execution_id": thread["configurable"]["thread_id"],
               "user_request": "Generate the SAD for SR-487331",
               "program_type": "RAITT", "sr_id": "SR-487331"}

    logger.info("Starting agent run for %s", initial["sr_id"])
    await _stream(agent, initial, thread)

    while _is_waiting(agent, thread):
        payload = _get_interrupt(agent, thread)
        if payload is None:
            break
        resume = _prompt_human(payload)
        await _stream(agent, Command(resume=resume), thread)

    logger.info("Agent run complete.")

if __name__ == "__main__":
    asyncio.run(run())