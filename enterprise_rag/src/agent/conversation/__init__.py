"""Multi-turn conversation context — lazy exports."""

from __future__ import annotations

from typing import Any

__all__ = [
    "CondenseResult",
    "TurnContext",
    "build_llm_messages",
    "condense_turn",
    "load_session_history",
    "needs_condense",
    "prepare_turn",
    "resolve_chat_history",
    "trim_history",
    "truncate_assistant_for_history",
]


def __getattr__(name: str) -> Any:
    if name in ("CondenseResult", "TurnContext"):
        from agent.conversation.types import CondenseResult, TurnContext

        return {"CondenseResult": CondenseResult, "TurnContext": TurnContext}[name]
    if name == "prepare_turn":
        from agent.conversation.prepare import prepare_turn

        return prepare_turn
    if name in ("condense_turn", "needs_condense"):
        from agent.conversation.query_condense import condense_turn, needs_condense

        return {"condense_turn": condense_turn, "needs_condense": needs_condense}[name]
    if name in (
        "build_llm_messages",
        "load_session_history",
        "resolve_chat_history",
        "trim_history",
        "truncate_assistant_for_history",
    ):
        from agent.conversation import memory

        return getattr(memory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
