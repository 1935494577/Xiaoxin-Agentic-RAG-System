"""Retrieve + streaming answer with memory, kb/general routing, optional verifier."""

from __future__ import annotations

import json
from typing import Any, Iterator

from agent.answer_prompts import (
    general_system_prompt,
    general_user_content,
    kb_system_prompt,
    kb_user_content,
)
from agent.kb_judge import answer_indicates_kb_miss
from agent.answer_router import resolve_answer_mode
from agent.context_format import format_source_citation, source_ref_dict
from agent.conversation_context import build_llm_messages
from agent.nodes import retrieve_node
from agent.stream_verifier import run_stream_verifier
from config import settings
from evaluation.stream_langsmith import new_stream_tracer
from openai import OpenAI


def stream_rag_chat(state: dict[str, Any]) -> Iterator[str]:
    """Yield SSE lines: data: {json}\n\n"""
    init_state: dict[str, Any] = {
        "question": state["question"],
        "user_id": state.get("user_id", "demo"),
        "user_department": state.get("user_department", settings.default_department),
        "allowed_sources": state.get("allowed_sources"),
    }
    init_state.update(state)

    history: list[dict[str, Any]] = list(state.get("history") or [])
    mem = state.get("memory_config") or {}
    fast = bool(state.get("stream_fast_mode"))
    llm_runtime = {
        "llm_api_key": state.get("llm_api_key"),
        "llm_api_base": state.get("llm_api_base"),
        "chat_model": state.get("chat_model"),
        "llm_extra_headers": state.get("llm_extra_headers"),
    }

    trace = new_stream_tracer(state)
    trace_err: str | None = None

    yield _evt({"type": "status", "phase": "retrieving", "trace_id": trace.trace_id})

    try:
        with trace.span(
            "retrieve",
            "retriever",
            inputs={"question": state["question"], "stream_fast_mode": fast},
        ) as span_out:
            try:
                retrieved = retrieve_node(init_state)  # type: ignore[arg-type]
            except Exception as e:
                trace_err = str(e)
                raise
            ctx = retrieved.get("contexts") or []
            meta = retrieved.get("contexts_meta") or []
            rewritten = retrieved.get("rewritten_query") or state["question"]
            span_out.update(
                {
                    "rewritten_query": rewritten,
                    "context_count": len(ctx),
                    "contexts_meta": meta[:5],
                }
            )
    except Exception as e:
        trace.finish({}, error=str(e))
        yield _evt({"type": "error", "message": str(e), "trace_id": trace.trace_id})
        return

    with trace.span(
        "route",
        "chain",
        inputs={"question": state["question"], "context_count": len(ctx)},
    ) as route_out:
        answer_mode = resolve_answer_mode(
            ctx,
            meta,
            question=state["question"],
            kb_min_score=float(mem.get("kb_min_score", 0.55)),
            kb_min_rerank_score=float(mem.get("kb_min_rerank_score", 0.0)),
            kb_llm_judge=bool(mem.get("kb_llm_judge", True)),
            general_fallback_enabled=bool(mem.get("general_fallback_enabled", True)),
            llm_runtime=llm_runtime,
        )
        route_out["answer_mode"] = answer_mode

    api_key = (state.get("llm_api_key") or "").strip() or settings.openai_api_key
    api_base = (state.get("llm_api_base") or "").strip() or settings.openai_api_base
    if not api_key:
        trace.finish({}, error="未配置 API Key")
        yield _evt({"type": "error", "message": "未配置 API Key", "trace_id": trace.trace_id})
        return

    yield _evt(
        {
            "type": "status",
            "phase": "generating",
            "answer_mode": answer_mode,
            "trace_id": trace.trace_id,
        }
    )

    if answer_mode == "kb":
        system = kb_system_prompt(fast=fast)
        user_content = kb_user_content(ctx, state["question"])
    else:
        system = general_system_prompt()
        user_content = general_user_content(state["question"])

    messages = build_llm_messages(system=system, history=history, user_content=user_content)

    headers = state.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = state.get("chat_model") or settings.openai_chat_model
    temp = float(state.get("llm_temperature_answer") if state.get("llm_temperature_answer") is not None else 0.2)
    kw: dict[str, Any] = {"model": model, "messages": messages, "temperature": temp, "stream": True}
    mt = state.get("llm_max_tokens_answer")
    if mt is not None:
        kw["max_tokens"] = int(mt)

    parts: list[str] = []
    try:
        with trace.span(
            "draft",
            "llm",
            inputs={
                "model": model,
                "answer_mode": answer_mode,
                "message_count": len(messages),
                "stream": True,
            },
        ) as draft_out:
            try:
                for evt in _stream_tokens(client, kw, parts):
                    yield evt
            except Exception as e:
                trace_err = str(e)
                raise
            answer = "".join(parts).strip()
            draft_out.update({"answer_preview": answer[:400], "answer_len": len(answer)})
    except Exception as e:
        trace.finish({"answer_mode": answer_mode}, error=str(e))
        yield _evt({"type": "error", "message": str(e)[:400], "trace_id": trace.trace_id})
        return

    answer = "".join(parts).strip()
    verified = True

    # 兜底：仅当显式开启 kb_post_stream_fallback 时才二次 LLM（默认关，避免 draft+fallback）
    if (
        answer_mode == "kb"
        and bool(mem.get("kb_post_stream_fallback", False))
        and bool(mem.get("general_fallback_enabled", True))
        and answer_indicates_kb_miss(answer)
    ):
        yield _evt(
            {
                "type": "status",
                "phase": "fallback",
                "answer_mode": "general",
                "trace_id": trace.trace_id,
            }
        )
        answer_mode = "general"
        meta = []
        ctx = []
        parts = []
        system = general_system_prompt()
        user_content = general_user_content(state["question"])
        messages = build_llm_messages(system=system, history=history, user_content=user_content)
        gen_kw: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temp,
            "stream": True,
        }
        if mt is not None:
            gen_kw["max_tokens"] = int(mt)
        with trace.span("fallback", "llm", inputs={"model": model, "stream": True}) as fb_out:
            try:
                for evt in _stream_tokens(client, gen_kw, parts):
                    yield evt
                answer = "".join(parts).strip()
                fb_out.update({"answer_len": len(answer)})
            except Exception:
                pass

    if answer_mode == "kb" and bool(mem.get("stream_verifier_enabled", False)):
        runtime = {
            "llm_api_key": api_key,
            "llm_api_base": api_base,
            "chat_model": model,
            "llm_temperature_verifier": state.get("llm_temperature_verifier"),
            "llm_max_tokens_verifier": state.get("llm_max_tokens_verifier"),
            "llm_extra_headers": headers,
        }
        with trace.span(
            "verifier",
            "llm",
            inputs={"answer_mode": answer_mode, "answer_len": len(answer)},
        ) as ver_out:
            vout = run_stream_verifier(
                answer=answer,
                contexts=ctx,
                answer_mode=answer_mode,
                enabled=True,
                llm_runtime=runtime,
            )
            answer = str(vout.get("answer") or answer)
            verified = bool(vout.get("verified", True))
            ver_out.update({"verified": verified})

    refs = [m for m in meta if m.get("parent_id")] if answer_mode == "kb" else []
    sources = [format_source_citation(m) for m in refs]
    source_refs = [source_ref_dict(m) for m in refs]
    foot = "\n\n引用: " + "; ".join(sources) if sources and verified else ""
    full_answer = answer + foot

    done_payload = {
        "type": "done",
        "answer": full_answer,
        "rewritten_query": rewritten,
        "sources": sources if verified else [],
        "source_refs": source_refs if verified else [],
        "answer_mode": answer_mode,
        "verified": verified,
        "trace_id": trace.trace_id,
    }
    trace.finish(
        {
            "answer_mode": answer_mode,
            "verified": verified,
            "source_count": len(sources),
            "trace_id": trace.trace_id,
        },
        error=trace_err,
    )
    yield _evt(done_payload)


def _stream_tokens(client: OpenAI, kw: dict[str, Any], parts: list[str]) -> Iterator[str]:
    """Yield SSE token events; append text to parts."""
    stream = client.chat.completions.create(**kw)
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if not delta:
            continue
        parts.append(delta)
        yield _evt({"type": "token", "content": delta})


def _evt(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
