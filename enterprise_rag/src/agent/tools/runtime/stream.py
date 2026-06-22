"""Chat 流式集成：general 模式下启用 Agent 工具。"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from agent.answer_prompts import general_system_prompt, general_user_content
from agent.conversation.rolling_summary import augment_system_with_summary
from agent.conversation_context import build_llm_messages
from agent.llm_routing import model_for_task, routing_llm_runtime
from agent.tools.config.registry import enabled_tool_ids, load_tools_config
from agent.tools.runtime.loop import run_tool_loop, stream_answer_after_tools
from agent.reasoning_modes import should_use_tool_loop

ReplayFn = Callable[[list[str]], Iterator[str]]


def is_tools_active() -> bool:
    cfg = load_tools_config()
    return bool(cfg.get("chat_tools_enabled")) and bool(enabled_tool_ids(cfg))


def stream_general_answer(
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
    replay_tokens: ReplayFn,
    emit_tokens: bool,
) -> Iterator[str]:
    """
    general 回答路径：先跑工具循环，再流式补全。
    产出已格式化的 SSE 行；同时写入 parts 与 tool_trace_out。
    """
    enabled = enabled_tool_ids(load_tools_config())
    mem = state.get("memory_config") or {}
    reasoning_mode = str(state.get("agent_reasoning_mode") or mem.get("agent_reasoning_mode") or "react")
    use_tools = should_use_tool_loop(reasoning_mode, tools_enabled=bool(enabled) and is_tools_active())
    if bool(state.get("_realtime_tool_turn")):
        use_tools = bool(enabled) and is_tools_active()

    system = general_system_prompt(slots=prompt_slots, reasoning_mode=reasoning_mode)
    if use_tools:
        from agent.tools.builtins.datetime_cn import format_beijing_time_anchor
        from agent.tools.builtins.relationship_graph import set_relationship_graph_context
        from agent.tools.runtime.prompt import AGENT_TOOLS_REALTIME_POLICY

        set_relationship_graph_context(
            user_department=state.get("user_department"),
            max_hops=3,
        )
        system = (
            f"{system}\n\n{AGENT_TOOLS_REALTIME_POLICY}\n\n{format_beijing_time_anchor()}"
        )
        enabled = enabled | {"show_relationship_graph"}
    system = augment_system_with_summary(system, state.get("rolling_summary"))
    user_content = general_user_content(state["question"])
    messages = build_llm_messages(system=system, history=history, user_content=user_content)

    pending: list[dict[str, Any]] = []

    def emit(payload: dict[str, Any]) -> None:
        pending.append(payload)

    routing_rt = routing_llm_runtime(
        {
            "llm_api_key": state.get("llm_api_key"),
            "llm_api_base": state.get("llm_api_base"),
            "chat_model": model,
            "routing_model": state.get("routing_model"),
            "llm_extra_headers": state.get("llm_extra_headers"),
        }
    )
    condense_model = model_for_task(routing_rt, task="routing")

    if use_tools:
        text, trace = run_tool_loop(
            client,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            enabled_ids=enabled,
            emit=emit,
            user_question=str(state.get("question") or ""),
            condense_model=condense_model,
        )
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
