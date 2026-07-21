"""ReAct 工具循环（OpenAI-compatible）。

.. deprecated::
    task/auto 主编排已迁移至 Jnao ``make_lead_agent``（见 ``jnao_harness.lead_stream``）。
    本模块仅作 harness 不可用时的回退，以及 knowledge 快路径下的 realtime 工具辅助。
"""

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
    metering_state: dict[str, Any] | None = None,
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
        try:
            from api.token_usage_store import metering_meta_from_state, record_usage_object

            meta = metering_meta_from_state(metering_state)
            if not meta.get("question_preview") and question:
                meta["question_preview"] = question[:200]
            record_usage_object(
                getattr(resp, "usage", None),
                model=model,
                caller="tool_loop",
                **meta,
            )
        except Exception:
            pass
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
                    if ok and name == "show_relationship_graph":
                        from graph.viz import parse_graph_viz_from_tool_output

                        viz = parse_graph_viz_from_tool_output(output)
                        if viz:
                            emit({"type": "graph_viz", "graph": viz})
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
    metering_state: dict[str, Any] | None = None,
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
    stream = None
    try:
        stream = client.chat.completions.create(**{**kw, "stream_options": {"include_usage": True}})
    except Exception:
        stream = client.chat.completions.create(**kw)
    usage = None
    for chunk in stream:
        chunk_usage = getattr(chunk, "usage", None)
        if chunk_usage is not None:
            usage = chunk_usage
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta
    try:
        from api.token_usage_store import metering_meta_from_state, record_usage_object

        record_usage_object(
            usage,
            model=model,
            caller="answer",
            **metering_meta_from_state(metering_state),
        )
    except Exception:
        pass
