"""ReAct 工具循环（OpenAI-compatible）。"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

from agent.tools.config.registry import TOOL_DEFINITIONS, enabled_tool_ids, execute_tool
from agent.tools.protocol.openai import openai_tools_payload
from agent.tools.runtime.tool_context import (
    _last_user_question,
    prepare_tool_content_for_llm,
)

EmitFn = Callable[[dict[str, Any]], None]

MAX_TOOL_TURNS = 5


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def run_tool_loop(
    client: Any,
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.2,
    max_tokens: int | None = None,
    enabled_ids: set[str] | None = None,
    emit: EmitFn | None = None,
    user_question: str = "",
    condense_model: str | None = None,
    condense_enabled: bool | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """执行 tool_calls 直至模型返回文本。返回 (final_text, tool_trace)。"""
    enabled = enabled_ids if enabled_ids is not None else enabled_tool_ids()
    if not enabled:
        return "", []

    tools = openai_tools_payload(enabled, TOOL_DEFINITIONS)
    trace: list[dict[str, Any]] = []
    working = messages
    question = user_question.strip() or _last_user_question(working)

    for _ in range(MAX_TOOL_TURNS):
        kw: dict[str, Any] = {
            "model": model,
            "messages": working,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": temperature,
        }
        if max_tokens is not None:
            kw["max_tokens"] = max_tokens

        resp = client.chat.completions.create(**kw)
        msg = resp.choices[0].message
        finish = resp.choices[0].finish_reason

        if msg.tool_calls:
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
            working.append(assistant_msg)

            for tc in msg.tool_calls:
                name = tc.function.name
                args = _parse_arguments(tc.function.arguments)
                if emit:
                    emit({"type": "tool_call", "tool": name, "arguments": args})
                if name not in enabled:
                    output = f"工具未启用：{name}"
                    ok = False
                else:
                    try:
                        output = execute_tool(name, args)
                        ok = True
                    except Exception as e:
                        output = f"工具执行失败：{e}"
                        ok = False
                trace.append({"tool": name, "arguments": args, "output": output, "ok": ok})
                if emit:
                    emit({"type": "tool_result", "tool": name, "output": output, "ok": ok})
                working.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": prepare_tool_content_for_llm(
                            output,
                            tool_name=name,
                            question=question,
                            client=client,
                            condense_model=condense_model,
                            condense_enabled=condense_enabled,
                        ),
                    }
                )
            continue

        text = (msg.content or "").strip()
        if text or finish == "stop":
            return text, trace

    return "", trace


def stream_answer_after_tools(
    client: Any,
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> Iterator[str]:
    """工具轮次结束后流式输出最终回答（不再传 tools）。"""
    kw: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    if max_tokens is not None:
        kw["max_tokens"] = max_tokens
    stream = client.chat.completions.create(**kw)
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta
