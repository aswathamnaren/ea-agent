"""Loads externalised prompts from prompts/*.md.

Prompts are knowledge, not code (PROJECT_CONTEXT §24). Architects edit the
Markdown files; no Python change is required. Results are cached so files are
read once per process, but a reload() is provided for hot-editing in dev.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path


class PromptLoader:
    """Reads prompt Markdown files from a base directory by logical name."""

    def __init__(self, prompts_dir: str | Path):
        self._dir = Path(prompts_dir)
        if not self._dir.is_dir():
            raise FileNotFoundError(f"Prompts directory not found: {self._dir}")

    @lru_cache(maxsize=64)
    def get(self, name: str) -> str:
        """Return the raw Markdown text for '<name>.md'.

        Example: get("decision_router") -> contents of decision_router.md
        """
        path = self._dir / f"{name}.md"
        if not path.is_file():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    def render(self, name: str, **variables: object) -> str:
        """Load a prompt and substitute {placeholders} with keyword values."""
        template = self.get(name)
        return template.format(**variables)

    def reload(self) -> None:
        """Clear the cache so edited prompt files are re-read (dev only)."""
        self.get.cache_clear()