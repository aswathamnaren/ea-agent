"""LangGraph execution state. LangGraph is deliberately isolated here in the
Application layer; the Domain never sees it."""
from __future__ import annotations

from typing import Annotated, Any, TypedDict
from operator import add


class AgentState(TypedDict, total=False):
    # --- Input / context ---
    execution_id: str
    user_request: str
    program_type: str          # RAITT | FASTT | Legacy
    sr_id: str

    # --- Accumulated knowledge ---
    research: dict[str, Any]
    systems: list[dict[str, Any]]

    # --- Human-in-the-loop ---
    clarifications: list[dict[str, Any]]     # pending + answered questions
    pending_answers: dict[str, str]          # injected on resume

    # --- Reasoning ---
    confidence: dict[str, float]
    decisions: list[dict[str, Any]]

    # --- Generation ---
    sections: dict[str, str]

    # --- Control ---
    phase: str
    next_action: str
    validation_errors: Annotated[list[str], add]
    approved: bool
    events: Annotated[list[str], add]        # structured streaming events

    research_count: int = 0        # 👈 guard against infinite research loops
    validated: bool = False
    reviewed: bool = False