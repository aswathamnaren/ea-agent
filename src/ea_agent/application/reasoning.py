from __future__ import annotations

import json
from typing import Any

from ea_agent.domain.ports import ReasonerPort, PromptProviderPort


class ReasoningEngine:
    def __init__(self, reasoner: ReasonerPort, prompts: PromptProviderPort,
                 threshold: float = 0.85):
        self._reasoner = reasoner
        self._prompts = prompts
        self._threshold = threshold

    async def decide_next_action(self, state: dict[str, Any]) -> dict[str, Any]:
        result = await self._reasoner.reason_json(
            system_prompt=self._prompts.get("decision_router"),
            user_prompt=f"Current execution state:\n{self._summarise_state(state)}",
        )
        if not result or "next_action" not in result:
            result = {
                "next_action": "research" if not state.get("systems") else "clarify",
                "reason": "Fallback: could not parse reasoning output.",
                "confidence": {},
            }

        conf = result.get("confidence", {})
        overall = (sum(conf.values()) / len(conf)) if conf else 0.0
        has_open_criticals = any(
            q.get("tier") == "CRITICAL" and not q.get("answer")
            for q in state.get("clarifications", [])
        )
        if overall < self._threshold and result["next_action"] in {"generate", "reason"}:
            result["next_action"] = "clarify"
        if has_open_criticals and result["next_action"] in {"generate", "reason", "validate"}:
            result["next_action"] = "clarify"
        return result

    @staticmethod
    def _summarise_state(state: dict[str, Any]) -> str:
        return json.dumps({
            "program_type": state.get("program_type"),
            "sr_id": state.get("sr_id"),
            "has_research": bool(state.get("research")),
            "systems_found": len(state.get("systems", [])),
            "open_clarifications": [
                {"id": q["id"], "tier": q["tier"], "answered": bool(q.get("answer"))}
                for q in state.get("clarifications", [])
            ],
            "decisions_made": len(state.get("decisions", [])),
            "sections_generated": list(state.get("sections", {}).keys()),
            "approved": state.get("approved", False),
        }, indent=2)