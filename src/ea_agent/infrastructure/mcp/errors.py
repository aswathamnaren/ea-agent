from __future__ import annotations

from typing import Any


def looks_like_mcp_error(value: Any) -> bool:
    text = str(value).lower()

    return any(
        marker in text
        for marker in [
            "validation error",
            "missing required argument",
            "unexpected keyword argument",
            "unknown tool",
            "tool not found",
            "call[",
        ]
    )
