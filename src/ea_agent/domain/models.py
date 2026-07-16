"""Domain entities for the Enterprise Solution Architect Agent.

This layer is the heart of the application and must remain completely
independent of LangGraph, Bedrock, DynamoDB, MCP and FastAPI.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProgramType(str, Enum):
    RAITT = "RAITT"
    FASTT = "FASTT"
    LEGACY = "Legacy"


class ExecutionPhase(str, Enum):
    UNDERSTAND = "understand"
    RESEARCH = "research"
    CLARIFY = "clarify"
    REASON = "reason"
    GENERATE = "generate"
    VALIDATE = "validate"
    REVIEW = "review"
    AWAIT_APPROVAL = "await_approval"
    PUBLISH = "publish"
    COMPLETE = "complete"


class QuestionTier(str, Enum):
    CRITICAL = "CRITICAL"      # blocks diagram generation
    IMPORTANT = "IMPORTANT"    # affects scope/accuracy
    PREFERENCE = "PREFERENCE"  # affects structure


class ClarificationQuestion(BaseModel):
    """A single clarification the agent needs answered before generation."""
    id: str
    tier: QuestionTier
    topic: str
    context: str = Field(..., description="What was found and why it is ambiguous")
    question: str
    answer: Optional[str] = None


class ArchitectureDecision(BaseModel):
    """A justified architectural decision (REST vs Kafka, sync vs async...)."""
    topic: str
    decision: str
    alternatives: list[str] = Field(default_factory=list)
    trade_offs: str
    reasoning: str
    risks: list[str] = Field(default_factory=list)


class SystemImpact(BaseModel):
    unit_id: Optional[str] = None
    name: str
    change_level: str  # "Code+Config" | "Config" | "No Change"


class ConfidenceReport(BaseModel):
    """Confidence drives execution: below threshold -> clarify, don't assume."""
    requirement_understanding: float = 0.0
    enterprise_context: float = 0.0
    architecture_decision: float = 0.0
    diagram_accuracy: float = 0.0

    @property
    def overall(self) -> float:
        scores = [
            self.requirement_understanding,
            self.enterprise_context,
            self.architecture_decision,
            self.diagram_accuracy,
        ]
        return round(sum(scores) / len(scores), 3)


class SolutionDocument(BaseModel):
    """The SAD artefact — one of many outputs of the reasoning process."""
    sr_id: str
    program_type: ProgramType
    version: str = "1.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    sections: dict[str, str] = Field(default_factory=dict)  # section_name -> markdown
    systems: list[SystemImpact] = Field(default_factory=list)
    decisions: list[ArchitectureDecision] = Field(default_factory=list)