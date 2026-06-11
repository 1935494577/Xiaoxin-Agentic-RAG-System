"""Chat 流式集成：general 模式下启用 Agent 工具。"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from agent.answer_prompts import general_system_prompt, general_user_content
from agent.conversation_context import build_llm_messages
from agent.tools.config.registry import enabled_tool_ids, load_tools_config
from agent.tools.runtime.loop import run_tool_loop, stream_answer_after_tools
from agent.tools.runtime.prompt import AGENT_TOOLS_REALTIME_POLICY

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
    system = general_system_prompt(slots=prompt_slots)
    if enabled:
        system = f"{system}\n\n{AGENT_TOOLS_REALTIME_POLICY}"
    user_content = general_user_content(state["question"])
    messages = build_llm_messages(system=system, history=history, user_content=user_content)

    pending: list[dict[str, Any]] = []

    def emit(payload: dict[str, Any]) -> None:
        pending.append(payload)

    text, trace = run_tool_loop(
        client,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        enabled_ids=enabled,
        emit=emit,
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
