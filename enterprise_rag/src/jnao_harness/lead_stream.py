"""Stream task/auto turns via Jnao make_lead_agent (LangGraph runtime)."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import uuid
from collections.abc import Iterator
from typing import Any

from jnao_community.kb_context import bind_kb_run_context, clear_kb_run_context
from jnao_harness.availability import should_use_agent_lead
from jnao_harness.runtime_handles import HarnessRuntime, get_runtime

logger = logging.getLogger(__name__)


def _evt(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _extract_message_text(chunk: Any) -> str:
    try:
        from deerflow.utils.messages import message_to_text

        return message_to_text(chunk) or ""
    except Exception:
        if isinstance(chunk, dict):
            content = chunk.get("content")
            if isinstance(content, str):
                return content
        return str(chunk or "")


def _map_bridge_event(entry: Any, *, last_text: str, tool_trace: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Convert one StreamBridge entry to Jnao SSE payloads."""
    from deerflow.runtime import END_SENTINEL, HEARTBEAT_SENTINEL

    if entry is HEARTBEAT_SENTINEL or entry is END_SENTINEL:
        return [], last_text

    event = getattr(entry, "event", None) or ""
    data = getattr(entry, "data", None)
    out: list[dict[str, Any]] = []

    if event in ("messages", "messages/partial"):
        text = _extract_message_text(data)
        if len(text) > len(last_text):
            delta = text[len(last_text) :]
            if delta:
                out.append({"type": "token", "content": delta})
            last_text = text
        elif text and not last_text:
            out.append({"type": "token", "content": text})
            last_text = text
        return out, last_text

    if event == "updates" and isinstance(data, dict):
        for _node, node_data in data.items():
            if not isinstance(node_data, dict):
                continue
            messages = node_data.get("messages") or []
            for msg in messages:
                tool_calls = getattr(msg, "tool_calls", None) or (msg.get("tool_calls") if isinstance(msg, dict) else None)
                if tool_calls:
                    for tc in tool_calls:
                        name = getattr(tc, "name", None) or (tc.get("name") if isinstance(tc, dict) else "")
                        args = getattr(tc, "args", None) or (tc.get("args") if isinstance(tc, dict) else {})
                        out.append({"type": "tool_call", "tool": name, "arguments": args or {}})
                        tool_trace.append({"tool": name, "arguments": args or {}})
        return out, last_text

    return out, last_text


async def _run_lead_async(
    state: dict[str, Any],
    runtime: HarnessRuntime,
    out_q: queue.Queue[tuple[str, Any]],
) -> None:
    from deerflow.agents.lead_agent.agent import make_lead_agent
    from deerflow.runtime import END_SENTINEL, RunContext, RunStatus, run_agent

    thread_id = str(state.get("session_id") or state.get("user_id") or uuid.uuid4().hex)
    question = str(state.get("question") or "").strip()
    bind_kb_run_context(
        user_department=str(state.get("user_department") or "general"),
        allowed_sources=state.get("allowed_sources"),
        chat_model=state.get("chat_model"),
        llm_api_base=state.get("llm_api_base"),
        llm_api_key=state.get("llm_api_key"),
        top_k=5,
        skip_rerank=bool(state.get("skip_rerank")),
    )

    record = await runtime.run_manager.create_or_reject(
        thread_id,
        assistant_id=None,
        metadata={"source": "jnao_chat_stream"},
        kwargs={"input": {"messages": [{"role": "user", "content": question}]}},
        user_id=str(state.get("user_id") or "demo"),
    )

    ctx = RunContext(
        checkpointer=runtime.checkpointer,
        store=runtime.store,
        event_store=runtime.run_event_store,
        run_events_config=runtime.run_events_config,
        thread_store=runtime.thread_store,
    )

    task = asyncio.create_task(
        run_agent(
            runtime.stream_bridge,
            runtime.run_manager,
            record,
            ctx=ctx,
            agent_factory=make_lead_agent,
            graph_input={"messages": [{"role": "user", "content": question}]},
            config={
                "configurable": {"thread_id": thread_id},
                "context": {
                    "thread_id": thread_id,
                    "run_id": record.run_id,
                    "model_name": state.get("chat_model"),
                },
            },
            stream_modes=["messages", "updates"],
        )
    )

    last_text = ""
    tool_trace: list[dict[str, Any]] = []
    try:
        async for entry in runtime.stream_bridge.subscribe(record.run_id):
            if entry is END_SENTINEL:
                break
            payloads, last_text = _map_bridge_event(entry, last_text=last_text, tool_trace=tool_trace)
            for payload in payloads:
                out_q.put(("sse", payload))
        await task
        status = await runtime.run_manager.get(record.run_id)
        if status and status.status == RunStatus.error:
            out_q.put(("err", RuntimeError(getattr(status, "error", None) or "Jnao run failed")))
            return
        out_q.put(
            (
                "done",
                {
                    "answer": last_text,
                    "tool_trace": tool_trace,
                    "agent_thread_id": thread_id,
                    "agent_run_id": record.run_id,
                },
            )
        )
    except Exception as exc:
        out_q.put(("err", exc))
    finally:
        clear_kb_run_context()


def stream_agent_lead(state: dict[str, Any]) -> Iterator[str]:
    """Yield Jnao SSE lines for a Jnao lead-agent turn."""
    if not should_use_agent_lead(state):
        raise RuntimeError("Jnao lead path not enabled for this state")

    # Prefer exam-bank gate over free-form agent answers for take-exam intents
    try:
        from exam_bank.chat_exam_gate import (
            exam_gate_failure_response,
            iter_exam_gate_sse,
            resolve_exam_chat_gate,
        )

        gate = resolve_exam_chat_gate(
            str(state.get("question") or ""),
            reader_user_id=str(state.get("user_id") or "").strip() or None,
        )
        if gate and gate.get("handled"):
            for ev in iter_exam_gate_sse(gate):
                yield _evt(ev)
            return
    except Exception:
        logger.exception("exam chat gate failed on lead path")
        from exam_bank.chat_exam_gate import exam_gate_failure_response, iter_exam_gate_sse

        for ev in iter_exam_gate_sse(exam_gate_failure_response()):
            yield _evt(ev)
        return

    runtime = get_runtime()
    if runtime is None:
        raise RuntimeError("Jnao runtime not initialized")

    out_q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def _worker() -> None:
        try:
            asyncio.run(_run_lead_async(state, runtime, out_q))
        except Exception as exc:
            out_q.put(("err", exc))
        finally:
            out_q.put(("eof", None))

    threading.Thread(target=_worker, daemon=True).start()
    yield _evt({"type": "status", "phase": "agent_lead", "trace_id": state.get("trace_id")})

    parts: list[str] = []
    tool_trace: list[dict[str, Any]] = []
    while True:
        kind, payload = out_q.get()
        if kind == "eof":
            break
        if kind == "err":
            from api.stream_errors import format_stream_error

            yield _evt({"type": "error", "message": format_stream_error(payload)})
            return
        if kind == "sse":
            if payload.get("type") == "token":
                parts.append(str(payload.get("content") or ""))
            elif payload.get("type") == "tool_call":
                tool_trace.append(
                    {
                        "tool": payload.get("tool"),
                        "arguments": payload.get("arguments"),
                    }
                )
            yield _evt(payload)
        if kind == "done":
            answer = str(payload.get("answer") or "".join(parts))
            yield _evt(
                {
                    "type": "done",
                    "answer": answer,
                    "sources": [],
                    "source_refs": [],
                    "answer_mode": "agent_lead",
                    "rag_architecture": "agentic",
                    "verified": True,
                    "tool_trace": payload.get("tool_trace") or tool_trace,
                    "agent_thread_id": payload.get("agent_thread_id"),
                    "agent_run_id": payload.get("agent_run_id"),
                }
            )
            return
