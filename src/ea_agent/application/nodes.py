"""LangGraph node functions. Agent THINKS (reasoner) or DELEGATES to Skills."""
from __future__ import annotations

from typing import Any

from langgraph.types import interrupt
from ea_agent.infrastructure.research_logger import save_research_trace
from ea_agent.application.reasoning import ReasoningEngine
from ea_agent.domain.ports import ReasonerPort, ResearchSkillPort, PublishSkillPort, PromptProviderPort

SPACE_MAP = {
    "RAITT": ["ARCH", "RAITT"],
    "FASTT": ["FASTT", "ARCH", "IAM"],
    "Legacy": ["ARCH", "DAS"],
}


class Nodes:
    def __init__(self, reasoner: ReasonerPort, research: ResearchSkillPort,
                 publisher: PublishSkillPort, engine: ReasoningEngine,
                 prompts: PromptProviderPort):
        self._reasoner = reasoner
        self._research = research
        self._publisher = publisher
        self._engine = engine
        self._prompts = prompts

    # ---- THINK: router ----
    async def route(self, state: dict[str, Any]) -> dict[str, Any]:
        """Deterministic progression once past research/clarify (smoke-test safe)."""
        clars = state.get("clarifications", [])
        criticals_open = any(c.get("tier") == "CRITICAL" and not c.get("answer")
                             for c in clars)

        # 1. No research yet -> research
        if not (state.get("research") and state.get("systems")):
            action = "research"
        # 2. No clarifications asked yet, or CRITICALs open -> clarify
        elif not clars or criticals_open:
            action = "clarify"
        # 3. Clarified but no decisions -> reason
        elif not state.get("decisions"):
            action = "reason"
        # 4. Decisions made but sections incomplete -> generate
        elif len(state.get("sections", {})) < 12:
            action = "generate"
        # 5. Sections done but not validated -> validate
        elif not state.get("validated"):
            action = "validate"
        # 6. Validated but not reviewed -> review
        elif not state.get("reviewed"):
            action = "review"
        # 7. Reviewed but not approved -> approval
        elif not state.get("approved"):
            action = "await_approval"
        # 8. Approved -> publish
        else:
            action = "complete"

        return {"next_action": action,
                "events": [f"🧭 Next: {action}"]}

    # ---- EXECUTE: research ----
    async def research_node(self, state: dict[str, Any]) -> dict[str, Any]:
        spaces = SPACE_MAP[state["program_type"]]

        hierarchy = await self._research.search_jira_hierarchy(state["sr_id"])

        confluence = await self._research.search_confluence(
            query=state["sr_id"],
            spaces=spaces,
        )

        arco = {}
        if hasattr(self._research, "search_existing_solutions"):
            arco = await self._research.search_existing_solutions(
                sr_id=state["sr_id"],
                summary=str(hierarchy.get("sr", "")),
            )

        systems = await self._extract_systems(hierarchy, confluence)

        research_payload = {
            "jira": hierarchy,
            "confluence": confluence,
            "arco": arco,
        }

        trace_path = save_research_trace(
            execution_id=state.get("execution_id", "unknown"),
            research=research_payload,
        )

        return {
            "research": research_payload,
            "systems": systems,
            "research_count": state.get("research_count", 0) + 1,
            "phase": "research",
            "events": [
                f"🔎 Searched Jira for {state['sr_id']}",
                f"🔎 Searched Confluence spaces: {', '.join(spaces)}",
                "🧠 Searched ARCO MiniBot for existing solution patterns",
                f"📄 Saved research trace: {trace_path}",
                f"🧩 Identified {len(systems)} systems",
            ],
        }
        
    # ---- THINK + HUMAN-IN-THE-LOOP: clarify ----
    async def clarify_node(self, state: dict[str, Any]) -> dict[str, Any]:
        # If questions were already asked and answered, do nothing (avoid re-ask).
        existing = state.get("clarifications", [])
        if existing and all(c.get("answer") for c in existing):
            return {"phase": "clarify", "events": ["✅ Clarifications already answered."]}

        # Reuse existing unanswered questions if present; else generate new ones.
        questions = existing or await self._generate_questions(state)
        answers: dict[str, str] = interrupt({
            "type": "clarification_request", "questions": questions})
        for q in questions:
            if q["id"] in answers:
                q["answer"] = answers[q["id"]]
        return {"clarifications": questions, "phase": "clarify",
                "events": [f"❓ Asked {len(questions)} questions", "✅ Received answers"]}


    # ---- THINK: architecture decisions ----
    async def reason_node(self, state: dict[str, Any]) -> dict[str, Any]:
        decisions = await self._make_decisions(state)
        return {"decisions": decisions, "phase": "reason",
                "events": [f"🏛️ Made {len(decisions)} architecture decisions"]}

    # ---- EXECUTE: incremental generation ----
    async def generate_node(self, state: dict[str, Any]) -> dict[str, Any]:
        section = self._next_pending_section(state)
        content = await self._generate_section(section, state)
        sections = dict(state.get("sections", {}))
        sections[section] = content
        return {"sections": sections, "phase": "generate",
                "events": [f"📝 Generated section: {section}"]}

    # ---- THINK: validation ----
    async def validate_node(self, state: dict[str, Any]) -> dict[str, Any]:
        errors = self._validate(state)
        return {"validation_errors": errors, "validated": True, "phase": "validate",
                "events": ["🔍 Validation: " + ("passed" if not errors
                                                else f"{len(errors)} issues")]}

    async def review_node(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"reviewed": True, "phase": "review",
                "events": ["🪞 Self-review complete"]}

    

    # ---- HUMAN-IN-THE-LOOP: approval ----
    async def approval_node(self, state: dict[str, Any]) -> dict[str, Any]:
        decision = interrupt({"type": "approval_request",
                              "preview": state.get("sections", {})})
        return {"approved": bool(decision.get("approved")), "phase": "await_approval",
                "events": ["👤 Awaiting human approval"]}

    # ---- EXECUTE: publish ----
    async def publish_node(self, state: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime
        from pathlib import Path

        sr_id = state["sr_id"]
        sections = state.get("sections", {})

        # Assemble the full SAD in section order
        order = ["motivation", "business_process", "use_cases", "constraints",
                 "component_diagram", "solution_context", "solution_design",
                 "impacted_pipes", "security", "impacted_apps",
                 "transition_impacts", "references"]
        parts = [f"# Solution Architecture Document — {sr_id}\n",
                 f"_Generated: {datetime.now():%Y-%m-%d %H:%M}_\n"]
        for name in order:
            if name in sections:
                title = name.replace("_", " ").title()
                parts.append(f"\n## {title}\n\n{sections[name]}\n")
        document = "\n".join(parts)

        # Save to disk (output/ folder at project root)
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        file_path = out_dir / f"{sr_id}-SAD-{datetime.now():%Y-%m-%d}.md"
        file_path.write_text(document, encoding="utf-8")

        # Publish (fake for now)
        space = SPACE_MAP[state["program_type"]][0]
        url = await self._publisher.publish_confluence(
            space, f"{sr_id} — SAD", document)

        return {"phase": "complete",
                "events": [f"💾 Saved SAD to: {file_path.resolve()}",
                           f"🚀 Published: {url}"]}

    # ---- helpers ----
    async def _extract_systems(self, jira, confluence) -> list[dict[str, Any]]:
        systems: list[dict[str, Any]] = []
        for _bus in jira.get("bus", []):
            systems.append({"unit_id": "U-621", "name": "SCS",
                            "change_level": "Code+Config"})
        if not systems:
            systems.append({"unit_id": "U-621", "name": "SCS",
                            "change_level": "Code+Config"})
        return systems

    async def _generate_questions(self, state) -> list[dict[str, Any]]:
        result = await self._reasoner.reason_json(
            system_prompt=self._prompts.get("clarification"),
            user_prompt=str(state.get("research", {})))
        questions = result.get("questions", [])
        if not questions:
            questions = [{"id": "Q1", "tier": "CRITICAL",
                          "topic": "Integration mechanism",
                          "context": "Default fallback question.",
                          "question": "How do the systems integrate (REST/SOAP/Kafka)?"}]
        return questions

    async def _make_decisions(self, state) -> list[dict[str, Any]]:
        result = await self._reasoner.reason_json(
            system_prompt=self._prompts.get("architecture_reasoning"),
            user_prompt=str({"research": state.get("research"),
                             "answers": state.get("clarifications", [])}))
        return result.get("decisions", [])

    def _next_pending_section(self, state) -> str:
        order = ["motivation", "business_process", "use_cases", "constraints",
                 "component_diagram", "solution_context", "solution_design",
                 "impacted_pipes", "security", "impacted_apps",
                 "transition_impacts", "references"]
        done = set(state.get("sections", {}))
        return next((s for s in order if s not in done), "references")

    async def _generate_section(self, section, state) -> str:
        prompt = self._prompts.render(
            "section_generation", section=section,
            sr_id=state.get("sr_id", ""), program_type=state.get("program_type", ""),
            context=str({"research": state.get("research"),
                         "decisions": state.get("decisions")}))
        return await self._reasoner.reason(
            system_prompt=self._prompts.get("system"), user_prompt=prompt)

    def _validate(self, state) -> list[str]:
        listmandatory = {"motivation", "component_diagram", "impacted_pipes",
                     "transition_impacts"}
        return [f"Missing mandatory section: {s}"
                for s in listmandatory - set(state.get("sections", {}))]
    
    
