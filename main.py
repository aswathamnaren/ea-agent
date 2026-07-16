"""Composition root + interrupt/resume driver."""
from __future__ import annotations

import asyncio
import logging
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from ea_agent.application.nodes import Nodes
from ea_agent.application.reasoning import ReasoningEngine
from ea_agent.application.workflow import build_agent
from ea_agent.config.settings import get_settings
from ea_agent.infrastructure.bedrock_reasoner import BedrockReasoner
from ea_agent.infrastructure.prompt_loader import PromptLoader
from ea_agent.infrastructure.fake_skills import FakeResearchSkill, FakePublishSkill

logger = logging.getLogger("ea_agent")


def _build_agent():
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    profile = settings.bedrock.profile if not settings.is_production else None
    reasoner = BedrockReasoner(model_id=settings.bedrock.model_id,
                               region=settings.bedrock.region, profile=profile)
    prompts = PromptLoader(settings.agent.prompts_dir)

    research = FakeResearchSkill()      # smoke-test fakes (no MCP needed)
    publisher = FakePublishSkill()

    engine = ReasoningEngine(reasoner, prompts,
                             threshold=settings.agent.confidence_threshold)
    nodes = Nodes(reasoner, research, publisher, engine, prompts)
    return build_agent(nodes, checkpointer=MemorySaver())


async def _stream(agent, payload, config) -> dict:
    last: dict = {}
    async for event in agent.astream(payload, config=config, stream_mode="values"):
        for msg in event.get("events", []):
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
    return answers


async def run() -> None:
    agent = _build_agent()
    thread = {"configurable": {"thread_id": str(uuid.uuid4())},
              "recursion_limit": 50}
    initial = {"execution_id": thread["configurable"]["thread_id"],
               "user_request": "Generate the SAD for SR-485079",
               "program_type": "RAITT", "sr_id": "SR-485079"}

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