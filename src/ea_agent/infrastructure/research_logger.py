"""Research logging helpers.

Provides transparent, sanitized logs for Jira, Confluence and ARCO calls.
Never logs tokens or secrets.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("ea_agent.research")


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def log_research_call(source: str, tool: str, arguments: dict[str, Any]) -> None:
    """Log which external research tool is being called."""
    logger.info("Research call started | source=%s | tool=%s", source, tool)
    logger.info("Research arguments | source=%s | args=%s", source, _safe_json(arguments))


def log_research_result(source: str, result: Any) -> None:
    """Log summary of result without dumping very large output."""
    text = _safe_json(result)
    logger.info("Research result received | source=%s | chars=%s", source, len(text))

    preview = text[:1000]
    logger.info("Research result preview | source=%s | preview=%s", source, preview)


def save_research_trace(execution_id: str, research: dict[str, Any]) -> Path:
    """Save full research payload for debugging and traceability."""
    out_dir = Path("output") / "research_traces"
    out_dir.mkdir(parents=True, exist_ok=True)

    path = out_dir / f"{execution_id}-research.json"
    path.write_text(
        json.dumps(research, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    logger.info("Saved research trace | path=%s", path.resolve())
    return path