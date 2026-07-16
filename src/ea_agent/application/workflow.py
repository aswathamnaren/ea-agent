"""Assembles the LangGraph agent. The graph is a REASONING LOOP, not a
linear pipeline: every node returns to the router, which re-decides."""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from ea_agent.application.state import AgentState
from ea_agent.application.nodes import Nodes

_ACTION_TO_NODE = {
    "research": "research",
    "clarify": "clarify",
    "reason": "reason",
    "generate": "generate",
    "validate": "validate",
    "review": "review",
    "await_approval": "approval",
    "complete": "publish",
}


def build_agent(nodes: Nodes, checkpointer: BaseCheckpointSaver):
    g = StateGraph(AgentState)

    g.add_node("route", nodes.route)
    g.add_node("research", nodes.research_node)
    g.add_node("clarify", nodes.clarify_node)
    g.add_node("reason", nodes.reason_node)
    g.add_node("generate", nodes.generate_node)
    g.add_node("validate", nodes.validate_node)
    g.add_node("review", nodes.review_node)
    g.add_node("approval", nodes.approval_node)
    g.add_node("publish", nodes.publish_node)

    g.add_edge(START, "route")

    # The agentic decision: route -> chosen action node
    def pick(state: AgentState) -> str:
        action = state.get("next_action", "research")
        if action == "complete" and not state.get("approved"):
            return "approval"           # never publish without sign-off
        return _ACTION_TO_NODE.get(action, "research")

    g.add_conditional_edges("route", pick, {
        "research": "research", "clarify": "clarify", "reason": "reason",
        "generate": "generate", "validate": "validate", "review": "review",
        "approval": "approval", "publish": "publish",
    })

    # Every executed action loops BACK to the router to re-reason...
    for node in ["research", "clarify", "reason", "generate",
                 "validate", "review", "approval"]:
        g.add_edge(node, "route")

    # ...except publish, which terminates.
    g.add_edge("publish", END)

    # Checkpointer enables interrupt/resume + durable execution.
    return g.compile(checkpointer=checkpointer)
