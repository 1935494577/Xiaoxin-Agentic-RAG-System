"""Shared types for multi-turn conversation context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CondenseResult:
    """Output of L1 query condense + topic shift detection."""

    standalone_query: str
    topic_shift: bool
    used_llm: bool = False


@dataclass
class TurnContext:
    """Prepared context for one chat turn."""

    message: str
    retrieval_query: str
    topic_shift: bool
    history_for_llm: list[dict[str, Any]]
    condense_used_llm: bool = False
    skip_retrieval_rewrite: bool = True
    rolling_summary: str = ""
    reset_context: bool = False
    meta: dict[str, Any] = field(default_factory=dict)
