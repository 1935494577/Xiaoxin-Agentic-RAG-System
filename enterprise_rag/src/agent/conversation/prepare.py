"""Orchestrate L1–L3 for one chat turn."""

from __future__ import annotations

from typing import Any

from agent.conversation.history_prune import prune_history_by_embedding
from agent.conversation.memory import trim_history, truncate_assistant_for_history
from agent.conversation.query_condense import condense_turn
from agent.conversation.types import CondenseResult, TurnContext


def _mem_bool(mem: dict[str, Any], key: str, default: bool) -> bool:
    val = mem.get(key)
    if val is None:
        return default
    return bool(val)


def _mem_int(mem: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(mem.get(key, default))
    except (TypeError, ValueError):
        return default


def _mem_float(mem: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(mem.get(key, default))
    except (TypeError, ValueError):
        return default


def _soften_history(history: list[dict[str, Any]], *, assistant_max_chars: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in history:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")
        if role == "assistant" and assistant_max_chars > 0:
            content = truncate_assistant_for_history(content, max_chars=assistant_max_chars)
        out.append({"role": role, "content": content})
    return out


def prepare_turn(
    *,
    message: str,
    history: list[dict[str, Any]],
    memory_config: dict[str, Any] | None = None,
    llm_runtime: dict[str, Any] | None = None,
    max_tokens_condense: int | None = None,
    rolling_summary: str | None = None,
    reset_context: bool = False,
) -> TurnContext:
    """
    Trim → condense (optional) → prune or clear history → attach rolling summary.
    reset_context=True：清空 history、视为换题、忽略旧摘要。
    """
    mem = memory_config or {}
    max_turns = _mem_int(mem, "max_history_turns", 6)
    max_chars = _mem_int(mem, "max_history_chars", 6000)
    assistant_cap = _mem_int(mem, "history_assistant_max_chars", 600)
    msg = message.strip()

    if reset_context:
        trimmed: list[dict[str, Any]] = []
        cond = CondenseResult(standalone_query=msg, topic_shift=True, used_llm=False)
        effective_summary = ""
    else:
        trimmed = trim_history(history, max_turns=max_turns, max_chars=max_chars)
        condense_on = _mem_bool(mem, "conversation_condense_enabled", True)

        if condense_on and trimmed:
            cond = condense_turn(
                msg,
                trimmed,
                llm_runtime=llm_runtime,
                max_tokens=max_tokens_condense,
                llm_enabled=_mem_bool(mem, "condense_llm_enabled", True),
            )
        else:
            cond = CondenseResult(standalone_query=msg, topic_shift=False, used_llm=False)

        if cond.topic_shift:
            effective_summary = ""
        elif _mem_bool(mem, "rolling_summary_enabled", True):
            effective_summary = (rolling_summary or "").strip()
        else:
            effective_summary = ""

    if reset_context or cond.topic_shift:
        history_for_llm: list[dict[str, Any]] = []
    elif _mem_bool(mem, "history_prune_enabled", True) and trimmed:
        history_for_llm = prune_history_by_embedding(
            cond.standalone_query,
            trimmed,
            min_similarity=_mem_float(mem, "history_prune_min_similarity", 0.35),
            max_turns=_mem_int(mem, "history_prune_max_turns", 4),
        )
        history_for_llm = trim_history(history_for_llm, max_turns=max_turns, max_chars=max_chars)
    else:
        history_for_llm = list(trimmed)

    history_for_llm = _soften_history(history_for_llm, assistant_max_chars=assistant_cap)

    return TurnContext(
        message=msg,
        retrieval_query=cond.standalone_query or msg,
        topic_shift=bool(reset_context or cond.topic_shift),
        history_for_llm=history_for_llm,
        condense_used_llm=cond.used_llm,
        skip_retrieval_rewrite=True,
        rolling_summary=effective_summary,
        reset_context=bool(reset_context),
        meta={
            "condense_used_llm": cond.used_llm,
            "history_turns_in": len(history),
            "history_turns_out": len(history_for_llm),
            "reset_context": bool(reset_context),
            "has_rolling_summary": bool(effective_summary),
        },
    )
