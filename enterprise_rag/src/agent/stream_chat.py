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

    yield _evt({"type": "status", "phase": "retrieving"})

    try:
        retrieved = retrieve_node(init_state)  # type: ignore[arg-type]
    except Exception as e:
        yield _evt({"type": "error", "message": str(e)})
        return

    ctx = retrieved.get("contexts") or []
    meta = retrieved.get("contexts_meta") or []
    rewritten = retrieved.get("rewritten_query") or state["question"]

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

    api_key = (state.get("llm_api_key") or "").strip() or settings.openai_api_key
    api_base = (state.get("llm_api_base") or "").strip() or settings.openai_api_base
    if not api_key:
        yield _evt({"type": "error", "message": "未配置 API Key"})
        return

    yield _evt({"type": "status", "phase": "generating", "answer_mode": answer_mode})

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
        for evt in _stream_tokens(client, kw, parts):
            yield evt
    except Exception as e:
        yield _evt({"type": "error", "message": str(e)[:400]})
        return

    answer = "".join(parts).strip()
    verified = True

    # 兜底：KB 仍声明资料不足 → 通知前端清空，再流式输出通用回答
    if (
        answer_mode == "kb"
        and bool(mem.get("general_fallback_enabled", True))
        and answer_indicates_kb_miss(answer)
    ):
        yield _evt({"type": "status", "phase": "fallback", "answer_mode": "general"})
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
        try:
            for evt in _stream_tokens(client, gen_kw, parts):
                yield evt
            answer = "".join(parts).strip()
        except Exception:
            pass

    if answer_mode == "kb" and bool(mem.get("stream_verifier_enabled", True)):
        runtime = {
            "llm_api_key": api_key,
            "llm_api_base": api_base,
            "chat_model": model,
            "llm_temperature_verifier": state.get("llm_temperature_verifier"),
            "llm_max_tokens_verifier": state.get("llm_max_tokens_verifier"),
            "llm_extra_headers": headers,
        }
        vout = run_stream_verifier(
            answer=answer,
            contexts=ctx,
            answer_mode=answer_mode,
            enabled=True,
            llm_runtime=runtime,
        )
        answer = str(vout.get("answer") or answer)
        verified = bool(vout.get("verified", True))

    refs = [m for m in meta if m.get("parent_id")] if answer_mode == "kb" else []
    sources = [format_source_citation(m) for m in refs]
    source_refs = [source_ref_dict(m) for m in refs]
    foot = "\n\n引用: " + "; ".join(sources) if sources and verified else ""
    full_answer = answer + foot

    yield _evt(
        {
            "type": "done",
            "answer": full_answer,
            "rewritten_query": rewritten,
            "sources": sources if verified else [],
            "source_refs": source_refs if verified else [],
            "answer_mode": answer_mode,
            "verified": verified,
        }
    )


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
