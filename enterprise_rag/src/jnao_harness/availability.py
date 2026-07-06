"""Detect Jnao harness availability and when to use lead-agent path."""

from __future__ import annotations

from typing import Any

from agent.runtime.modes import AssistantMode, normalize_assistant_mode


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


def should_use_agent_lead(state: dict[str, Any]) -> bool:
    """task/auto modes use make_lead_agent when harness is installed."""
    if not harness_available():
        return False
    mode = resolve_assistant_mode(state)
    return mode in ("task", "auto")
