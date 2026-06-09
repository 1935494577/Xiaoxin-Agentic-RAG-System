"""Retrieve + streaming answer (skip verifier for responsive SSE)."""

from __future__ import annotations

import json
from typing import Any, Iterator

from agent.context_format import format_source_citation, source_ref_dict
from agent.nodes import retrieve_node
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

    yield _evt({"type": "status", "phase": "retrieving"})

    try:
        retrieved = retrieve_node(init_state)  # type: ignore[arg-type]
    except Exception as e:
        yield _evt({"type": "error", "message": str(e)})
        return

    ctx = retrieved.get("contexts") or []
    meta = retrieved.get("contexts_meta") or []
    rewritten = retrieved.get("rewritten_query") or state["question"]

    api_key = (state.get("llm_api_key") or "").strip() or settings.openai_api_key
    api_base = (state.get("llm_api_base") or "").strip() or settings.openai_api_base
    if not api_key:
        yield _evt({"type": "error", "message": "未配置 API Key"})
        return

    yield _evt({"type": "status", "phase": "generating"})

    body = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(ctx))
    headers = state.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = state.get("chat_model") or settings.openai_chat_model
    temp = float(state.get("llm_temperature_answer") if state.get("llm_temperature_answer") is not None else 0.2)
    fast = bool(state.get("stream_fast_mode"))
    system = (
        "你是企业知识库助手。仅依据参考资料作答；资料不足请说明。回答简洁。"
        if fast
        else "你是企业知识库助手。仅依据参考资料作答；资料不足请说明。"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"参考资料：\n{body}\n\n用户问题：{state['question']}"},
    ]
    kw: dict[str, Any] = {"model": model, "messages": messages, "temperature": temp, "stream": True}
    mt = state.get("llm_max_tokens_answer")
    if mt is not None:
        kw["max_tokens"] = int(mt)

    parts: list[str] = []
    try:
        stream = client.chat.completions.create(**kw)
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue
            parts.append(delta)
            yield _evt({"type": "token", "content": delta})
    except Exception as e:
        yield _evt({"type": "error", "message": str(e)[:400]})
        return

    answer = "".join(parts).strip()
    refs = [m for m in meta if m.get("parent_id")]
    sources = [format_source_citation(m) for m in refs]
    source_refs = [source_ref_dict(m) for m in refs]
    foot = "\n\n引用: " + "; ".join(sources) if sources else ""
    full_answer = answer + foot

    yield _evt(
        {
            "type": "done",
            "answer": full_answer,
            "rewritten_query": rewritten,
            "sources": sources,
            "source_refs": source_refs,
        }
    )


def _evt(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
