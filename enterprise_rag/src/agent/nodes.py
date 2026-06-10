from __future__ import annotations

from typing import Any, TypedDict

from openai import OpenAI

from config import settings
from agent.context_format import format_context_with_meta, format_source_citation, source_ref_dict
from agent.answer_router import resolve_answer_mode
from agent.answer_prompts import (
    general_system_prompt,
    general_user_content,
    kb_system_prompt,
    kb_user_content,
)
from agent.conversation_context import build_llm_messages
from security.guard import scan_prompt_injection
from security.permissions import filter_by_sources


class AgentState(TypedDict, total=False):
    question: str
    user_id: str
    user_department: str
    allowed_sources: list[str] | None
    chat_model: str | None
    llm_api_base: str | None
    llm_api_key: str | None
    llm_extra_headers: dict[str, Any] | None
    llm_temperature_answer: float | None
    llm_temperature_verifier: float | None
    llm_max_tokens_rewrite: int | None
    llm_max_tokens_answer: int | None
    llm_max_tokens_verifier: int | None
    route_next: str
    rewritten_query: str
    contexts: list[str]
    contexts_meta: list[dict[str, Any]]
    answer: str
    answer_mode: str
    verified: bool
    sources: list[str]
    source_refs: list[dict[str, Any]]
    verifier_decision: str
    retry_count: int
    history: list[dict[str, Any]]
    memory_config: dict[str, Any]


def router_node(state: AgentState) -> dict[str, Any]:
    ok, reason = scan_prompt_injection(state["question"])
    if not ok:
        return {"route_next": "reject", "answer": reason or "拒绝回答", "sources": [], "verified": False}
    if len(state["question"].strip()) < 2:
        return {"route_next": "reject", "answer": "问题过短", "sources": [], "verified": False}
    return {"route_next": "retrieve"}


def retrieve_node(state: AgentState) -> dict[str, Any]:
    from retrieval.hybrid_searcher import hybrid_search

    dept = state.get("user_department") or settings.default_department
    skip_rw = state.get("skip_query_rewrite")
    rk = state.get("retrieve_top_k")
    rerank_k = state.get("rerank_top_k")
    rw, parents = hybrid_search(
        state["question"],
        dept,
        top_k=int(rerank_k) if rerank_k is not None else settings.rerank_top_k,
        chat_model=state.get("chat_model"),
        llm_api_base=state.get("llm_api_base"),
        llm_api_key=state.get("llm_api_key"),
        llm_max_tokens_rewrite=state.get("llm_max_tokens_rewrite"),
        llm_extra_headers=state.get("llm_extra_headers"),
        skip_query_rewrite=skip_rw,
        retrieve_top_k=int(rk) if rk is not None else None,
        skip_rerank=bool(state.get("skip_rerank")),
        rerank_top_k=int(rerank_k) if rerank_k is not None else None,
        pre_rerank_k=state.get("pre_rerank_k"),
    )
    parents = filter_by_sources(parents, state.get("allowed_sources"))
    max_chars = state.get("context_max_chars")
    if max_chars and int(max_chars) > 0:
        limit = int(max_chars)
        for p in parents:
            text = str(p.get("text") or "")
            if len(text) > limit:
                p["text"] = text[:limit] + "…"
    return {
        "rewritten_query": rw,
        "contexts": [format_context_with_meta(p) for p in parents],
        "contexts_meta": parents,
    }


def answer_node(state: AgentState) -> dict[str, Any]:
    ctx = state.get("contexts") or []
    meta = state.get("contexts_meta") or []
    mem = state.get("memory_config") or {}
    history = list(state.get("history") or [])

    answer_mode = resolve_answer_mode(
        ctx,
        meta,
        question=state["question"],
        kb_min_score=float(mem.get("kb_min_score", 0.55)),
        kb_min_rerank_score=float(mem.get("kb_min_rerank_score", 0.0)),
        kb_llm_judge=bool(mem.get("kb_llm_judge", True)),
        general_fallback_enabled=bool(mem.get("general_fallback_enabled", True)),
        llm_runtime={
            "llm_api_key": state.get("llm_api_key"),
            "llm_api_base": state.get("llm_api_base"),
            "chat_model": state.get("chat_model"),
            "llm_extra_headers": state.get("llm_extra_headers"),
        },
    )

    api_key = (state.get("llm_api_key") or "").strip() or settings.openai_api_key
    api_base = (state.get("llm_api_base") or "").strip() or settings.openai_api_base
    if not api_key:
        return {
            "answer": "未配置 API Key（请在模型配置页保存，或配置 .env 的 OPENAI_API_KEY）。",
            "verifier_decision": "pass",
            "verified": True,
            "answer_mode": answer_mode,
        }

    headers = state.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    retry_note = ""
    if int(state.get("retry_count") or 0) > 0:
        retry_note = "上一轮未通过一致性校验，请更严格依据资料重写。\n"

    mem = state.get("memory_config") or {}
    prompt_slots = mem.get("prompt_slots")

    if answer_mode == "kb":
        system = kb_system_prompt(fast=bool(state.get("stream_fast_mode")), slots=prompt_slots)
        user_content = retry_note + kb_user_content(ctx, state["question"])
    else:
        system = general_system_prompt(slots=prompt_slots)
        user_content = retry_note + general_user_content(state["question"])

    messages = build_llm_messages(system=system, history=history, user_content=user_content)
    model = state.get("chat_model") or settings.openai_chat_model
    temp = float(state.get("llm_temperature_answer") if state.get("llm_temperature_answer") is not None else 0.2)
    kw: dict[str, Any] = {"model": model, "messages": messages, "temperature": temp}
    mt = state.get("llm_max_tokens_answer")
    if mt is not None:
        kw["max_tokens"] = int(mt)
    resp = client.chat.completions.create(**kw)
    ans = (resp.choices[0].message.content or "").strip()
    return {"answer": ans, "answer_mode": answer_mode}


def verifier_node(state: AgentState) -> dict[str, Any]:
    if state.get("answer_mode") == "general":
        return {"verifier_decision": "pass", "verified": True}

    mem = state.get("memory_config") or {}
    if not bool(mem.get("graph_verifier_enabled", False)):
        return {"verifier_decision": "pass", "verified": True}

    api_key = (state.get("llm_api_key") or "").strip() or settings.openai_api_key
    api_base = (state.get("llm_api_base") or "").strip() or settings.openai_api_base
    if not api_key:
        return {"verifier_decision": "pass", "verified": True}
    ctx = state.get("contexts") or []
    body = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(ctx))
    ans = state.get("answer") or ""
    headers = state.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = state.get("chat_model") or settings.openai_chat_model
    temp = float(state.get("llm_temperature_verifier") if state.get("llm_temperature_verifier") is not None else 0.0)
    kw: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是答案一致性审查员。只输出一个词：PASS / RETRY / REJECT。",
            },
            {
                "role": "user",
                "content": f"资料：\n{body}\n\n答案：\n{ans}\n\n若答案明显超出资料或自相矛盾，输出RETRY（可重试）或REJECT（拒答）。",
            },
        ],
        "temperature": temp,
    }
    mt = state.get("llm_max_tokens_verifier")
    kw["max_tokens"] = int(mt) if mt is not None else 8
    resp = client.chat.completions.create(**kw)
    tag = (resp.choices[0].message.content or "").strip().upper()
    retries = int(state.get("retry_count") or 0)
    if "RETRY" in tag and retries < 2:
        return {"verifier_decision": "retry", "retry_count": retries + 1}
    if "REJECT" in tag:
        return {"verifier_decision": "reject", "answer": "无法根据资料确认，已拒答。", "verified": False}
    return {"verifier_decision": "pass", "verified": True}


def citer_node(state: AgentState) -> dict[str, Any]:
    if state.get("answer_mode") == "general" or not state.get("verified", True):
        ans = state.get("answer") or ""
        return {"sources": [], "source_refs": [], "answer": ans}

    meta = state.get("contexts_meta") or []
    refs = [m for m in meta if m.get("parent_id")]
    sources = [format_source_citation(m) for m in refs]
    source_refs = [source_ref_dict(m) for m in refs]
    ans = state.get("answer") or ""
    from agent.kb_judge import should_attach_citations

    if not should_attach_citations(
        answer_mode="kb",
        answer=ans,
        contexts_meta=meta,
    ):
        sources = []
        source_refs = []
    return {"sources": sources, "source_refs": source_refs, "answer": ans}


def route_after_router(state: AgentState) -> str:
    return str(state.get("route_next") or "retrieve")


def route_after_verifier(state: AgentState) -> str:
    return str(state.get("verifier_decision") or "pass")
