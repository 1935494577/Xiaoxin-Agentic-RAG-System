"""Detect Jnao harness availability and when to use lead-agent path."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any, Literal

from agent.runtime.modes import AssistantMode, normalize_assistant_mode
from config import settings

logger = logging.getLogger(__name__)

ChatPipeline = Literal["lead_agent", "kb_fast"]


def harness_available() -> bool:
    try:
        import deerflow  # noqa: F401

        return True
    except ImportError:
        return False


def resolve_assistant_mode(state: dict[str, Any]) -> AssistantMode:
    raw = state.get("assistant_mode")
    if not raw:
        mem = state.get("memory_config") or {}
        raw = mem.get("_assistant_mode")
    return normalize_assistant_mode(str(raw or "auto"))


def resolve_chat_pipeline(state: dict[str, Any]) -> ChatPipeline:
    """Explicit stream routing: DeerFlow lead (task/auto) vs KB fast path (knowledge)."""
    if not settings.chat_lead_agent_enabled:
        return "kb_fast"
    if not harness_available():
        return "kb_fast"
    mode = resolve_assistant_mode(state)
    if mode in ("task", "auto"):
        return "lead_agent"
    return "kb_fast"


def should_use_agent_lead(state: dict[str, Any]) -> bool:
    """task/auto modes use make_lead_agent when harness is installed."""
    return resolve_chat_pipeline(state) == "lead_agent"


def stream_chat_events(state: dict[str, Any]) -> Iterator[str]:
    """Single entry for /chat/stream: lead agent with KB fallback."""
    from agent.stream_chat import stream_rag_chat

    pipeline = resolve_chat_pipeline(state)
    if pipeline == "lead_agent":
        from jnao_harness.lead_stream import stream_agent_lead

        try:
            yield from stream_agent_lead(state)
            return
        except Exception as exc:
            logger.warning(
                "Jnao lead stream failed, falling back to KB path: %s",
                exc,
                exc_info=True,
            )
    yield from stream_rag_chat(state)
