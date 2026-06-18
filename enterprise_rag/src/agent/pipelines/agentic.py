"""Agentic RAG: multi-turn KB search + optional web tools."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from agent.answer_prompts import general_system_prompt, general_user_content
from agent.conversation.rolling_summary import augment_system_with_summary
from agent.conversation_context import build_llm_messages
from agent.tools.builtins.kb_search import clear_kb_search_context, set_kb_search_context
from agent.tools.builtins.relationship_graph import (
    clear_relationship_graph_context,
    set_relationship_graph_context,
)
from agent.tools.config.registry import enabled_tool_ids, load_tools_config
from agent.tools.runtime.loop import run_tool_loop, stream_answer_after_tools


def run_agentic_retrieval(
    state: dict[str, Any],
    *,
    max_turns: int = 6,
) -> dict[str, Any]:
    """
    Run tool loop for investigation; collect KB hits into contexts_meta.
    Returns {contexts, contexts_meta, tool_trace, working_messages}.
    """
    from openai import OpenAI

    from config import settings

    mem = state.get("memory_config") or {}
    history = list(state.get("history") or [])
    reasoning_mode = "plan_execute"
    prompt_slots = mem.get("prompt_slots")
    rolling_summary = str(state.get("rolling_summary") or "")

    api_key = (state.get("llm_api_key") or "").strip() or settings.openai_api_key
    api_base = (state.get("llm_api_base") or "").strip() or settings.openai_api_base
    headers = state.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = state.get("chat_model") or settings.openai_chat_model
    temp = float(state.get("llm_temperature_answer") if state.get("llm_temperature_answer") is not None else 0.2)
    mt = state.get("llm_max_tokens_answer")
    mt_int = int(mt) if mt is not None else None

    set_kb_search_context(
        user_department=state.get("user_department"),
        allowed_sources=state.get("allowed_sources"),
        chat_model=state.get("chat_model"),
        llm_api_base=state.get("llm_api_base"),
        llm_api_key=state.get("llm_api_key"),
        top_k=5,
        skip_rerank=bool(state.get("skip_rerank")),
        hits=[],
    )
    set_relationship_graph_context(
        user_department=state.get("user_department"),
        max_hops=3,
    )

    cfg = load_tools_config()
    enabled = enabled_tool_ids(cfg)
    enabled = enabled | {"kb_search", "show_relationship_graph"}

    system = augment_system_with_summary(
        general_system_prompt(slots=prompt_slots, reasoning_mode=reasoning_mode)
        + "\n\n【Agentic RAG】你是调查分析助手。必须先用 kb_search 检索内部知识库，"
        "根据结果决定是否继续检索或补充 web_search。综合多轮结果给出结构化结论。",
        rolling_summary,
    )
    user_content = general_user_content(state["question"])
    messages = build_llm_messages(system=system, history=history, user_content=user_content)

    # Patch MAX_TOOL_TURNS via local loop import
    import agent.tools.runtime.loop as loop_mod

    old_max = loop_mod.MAX_TOOL_TURNS
    loop_mod.MAX_TOOL_TURNS = max_turns
    try:
        text, trace = run_tool_loop(
            client,
            model=model,
            messages=messages,
            temperature=temp,
            max_tokens=mt_int,
            enabled_ids=enabled,
            user_question=str(state.get("question") or ""),
        )
    finally:
        loop_mod.MAX_TOOL_TURNS = old_max

    from agent.tools.builtins.kb_search import get_kb_hits

    hits = get_kb_hits()
    clear_kb_search_context()
    clear_relationship_graph_context()

    from agent.context_format import format_context_with_meta

    meta = hits[:8]
    ctx = [format_context_with_meta(p) for p in meta]
    return {
        "contexts": ctx,
        "contexts_meta": meta,
        "tool_trace": trace,
        "agentic_preamble": text,
        "rewritten_query": state.get("retrieval_query") or state["question"],
    }


def stream_agentic_answer(
    *,
    state: dict[str, Any],
    client: Any,
    model: str,
    temperature: float,
    max_tokens: int | None,
    history: list[dict[str, Any]],
    prompt_slots: Any,
    parts: list[str],
    tool_trace_out: list[dict[str, Any]],
    emit_event: Callable[[dict[str, Any]], str],
    replay_tokens: Callable[[list[str]], Iterator[str]],
    emit_tokens: bool,
    max_turns: int = 6,
) -> Iterator[str]:
    """Stream agentic investigation then final answer."""
    mem = state.get("memory_config") or {}
    reasoning_mode = "plan_execute"
    rolling_summary = str(state.get("rolling_summary") or "")

    set_kb_search_context(
        user_department=state.get("user_department"),
        allowed_sources=state.get("allowed_sources"),
        chat_model=state.get("chat_model"),
        llm_api_base=state.get("llm_api_base"),
        llm_api_key=state.get("llm_api_key"),
        top_k=5,
        skip_rerank=bool(state.get("skip_rerank")),
        hits=[],
    )
    set_relationship_graph_context(
        user_department=state.get("user_department"),
        max_hops=3,
    )

    enabled = enabled_tool_ids(load_tools_config()) | {"kb_search", "show_relationship_graph"}

    system = augment_system_with_summary(
        general_system_prompt(slots=prompt_slots, reasoning_mode=reasoning_mode)
        + "\n\n【Agentic RAG】先用 kb_search 查知识库，必要时 web_search。"
        "用户询问人物关系、组织图、上下级时调用 show_relationship_graph 并在对话中展示关系图。"
        "最后给出完整分析。",
        rolling_summary,
    )
    user_content = general_user_content(state["question"])
    messages = build_llm_messages(system=system, history=history, user_content=user_content)

    pending: list[dict[str, Any]] = []

    def emit(payload: dict[str, Any]) -> None:
        pending.append(payload)

    import agent.tools.runtime.loop as loop_mod

    old_max = loop_mod.MAX_TOOL_TURNS
    loop_mod.MAX_TOOL_TURNS = max_turns
    try:
        text, trace = run_tool_loop(
            client,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            enabled_ids=enabled,
            emit=emit,
            user_question=str(state.get("question") or ""),
        )
    finally:
        loop_mod.MAX_TOOL_TURNS = old_max

    from agent.tools.builtins.kb_search import get_kb_hits

    state["_agentic_hits"] = get_kb_hits()
    clear_kb_search_context()
    clear_relationship_graph_context()

    tool_trace_out.extend(trace)
    for ev in pending:
        yield emit_event(ev)

    if text:
        parts.append(text)
        if emit_tokens:
            yield from replay_tokens([text])
        return

    for delta in stream_answer_after_tools(
        client,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    ):
        parts.append(delta)
        if emit_tokens:
            yield emit_event({"type": "token", "content": delta})
