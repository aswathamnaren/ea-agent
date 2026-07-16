from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def make_json_safe(value: Any) -> Any:
    """
    Convert MCP SDK / Pydantic / dataclass / arbitrary objects into
    JSON/msgpack-safe primitives before storing in LangGraph state.
    """

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(make_json_safe(k)): make_json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]

    # Important:
    # is_dataclass(value) is True for both dataclass instances and dataclass classes.
    # asdict() only works for dataclass instances, so exclude classes/types.
    if is_dataclass(value) and not isinstance(value, type):
        return make_json_safe(asdict(value))

    if hasattr(value, "model_dump"):
        try:
            return make_json_safe(value.model_dump(mode="json"))
        except Exception:
            try:
                return make_json_safe(value.model_dump())
            except Exception:
                return str(value)

    if hasattr(value, "dict"):
        try:
            return make_json_safe(value.dict())
        except Exception:
            return str(value)

    return str(value)