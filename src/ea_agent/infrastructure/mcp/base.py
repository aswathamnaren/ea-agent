"""Base MCP client abstractions.

Infrastructure only. No business reasoning here.
"""

from __future__ import annotations

import json
from typing import Any


def normalize_mcp_result(result: Any) -> Any:
    """Convert MCP tool result content into Python-friendly values.

    MCP tools commonly return content blocks. This helper extracts text blocks
    and parses JSON when possible.
    """
    if result is None:
        return None

    content = getattr(result, "content", None)
    if content is None:
        return result

    values: list[Any] = []

    for item in content:
        text = getattr(item, "text", None)
        if text is None:
            values.append(item)
            continue

        text = text.strip()
        if not text:
            continue

        try:
            values.append(json.loads(text))
        except json.JSONDecodeError:
            values.append(text)

    if len(values) == 1:
        return values[0]

    return values