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
from agent.kb_judge import answer_indicates_kb_miss, should_attach_citations
from agent.answer_router import resolve_answer_mode
from agent.context_format import build_source_citations
from agent.conversation_context import build_llm_messages
from agent.conversation.rolling_summary import augment_system_with_summary
from agent.llm_routing import routing_llm_runtime
from agent.nodes import retrieve_node
from agent.stream_verifier import run_stream_verifier
from agent.tools.runtime.stream import is_tools_active, stream_general_answer
from agent.tools.runtime.routing import question_needs_agent_tools
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
    rolling_summary = str(state.get("rolling_summary") or "")
    mem = state.get("memory_config") or {}
    fast = bool(state.get("stream_fast_mode"))
    prompt_slots = mem.get("prompt_slots")
    hybrid = bool(state.get("hybrid_expert_mode"))
    llm_runtime = routing_llm_runtime(
        {
            "llm_api_key": state.get("llm_api_key"),
            "llm_api_base": state.get("llm_api_base"),
            "chat_model": state.get("chat_model"),
            "routing_model": state.get("routing_model"),
            "llm_extra_headers": state.get("llm_extra_headers"),
        }
    )

    trace = new_stream_tracer(state)
    trace_err: str | None = None
    quiet = bool(state.get("quiet_routing"))

    if not quiet:
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
            topic_shift=bool(state.get("topic_shift")),
            kb_llm_judge_always=bool(mem.get("kb_llm_judge_always", False)),
            llm_runtime=llm_runtime,
        )
        if is_tools_active() and question_needs_agent_tools(state["question"]):
            answer_mode = "general"
            route_out["tool_route_override"] = True
        route_out["answer_mode"] = answer_mode

    api_key = (state.get("llm_api_key") or "").strip() or settings.openai_api_key
    api_base = (state.get("llm_api_base") or "").strip() or settings.openai_api_base
    if not api_key:
        trace.finish({}, error="未配置 API Key")
        yield _evt({"type": "error", "message": "未配置 API Key", "trace_id": trace.trace_id})
        return

    if not quiet:
        yield _evt(
            {
                "type": "status",
                "phase": "generating",
                "answer_mode": answer_mode,
                "trace_id": trace.trace_id,
            }
        )

    client, model, temp, mt = _llm_client(state, api_key, api_base)

    may_post_fallback = (
        answer_mode == "kb"
        and hybrid
        and bool(mem.get("kb_post_stream_fallback", False))
        and bool(mem.get("general_fallback_enabled", True))
    )
    fell_back_to_general = False

    parts: list[str] = []
    try:
        with trace.span(
            "draft",
            "llm",
            inputs={
                "model": model,
                "answer_mode": answer_mode,
                "buffered_kb": may_post_fallback,
                "stream": True,
            },
        ) as draft_out:
            tool_trace: list[dict[str, Any]] = []
            if answer_mode == "kb":
                system = augment_system_with_summary(
                    kb_system_prompt(fast=fast, slots=prompt_slots),
                    rolling_summary,
                )
                user_content = kb_user_content(ctx, state["question"])
                messages = build_llm_messages(system=system, history=history, user_content=user_content)
                kw = _gen_kw(model, messages, temp, mt)
                try:
                    if may_post_fallback:
                        for _ in _stream_tokens(client, kw, parts, emit=False):
                            pass
                    else:
                        yield from _stream_tokens(client, kw, parts, emit=True)
                except Exception as e:
                    trace_err = str(e)
                    raise
            elif is_tools_active():
                try:
                    yield from stream_general_answer(
                        state=state,
                        client=client,
                        model=model,
                        temperature=temp,
                        max_tokens=mt,
                        history=history,
                        prompt_slots=prompt_slots,
                        parts=parts,
                        tool_trace_out=tool_trace,
                        emit_event=_evt,
                        replay_tokens=_replay_tokens,
                        emit_tokens=not may_post_fallback,
                    )
                except Exception as e:
                    trace_err = str(e)
                    raise
            else:
                system = augment_system_with_summary(
                    general_system_prompt(slots=prompt_slots),
                    rolling_summary,
                )
                user_content = general_user_content(
                    state["question"],
                    contexts=ctx if hybrid and ctx else None,
                )
                messages = build_llm_messages(system=system, history=history, user_content=user_content)
                kw = _gen_kw(model, messages, temp, mt)
                try:
                    if may_post_fallback:
                        for _ in _stream_tokens(client, kw, parts, emit=False):
                            pass
                    else:
                        yield from _stream_tokens(client, kw, parts, emit=True)
                except Exception as e:
                    trace_err = str(e)
                    raise
            answer = "".join(parts).strip()
            draft_out.update(
                {
                    "answer_preview": answer[:400],
                    "answer_len": len(answer),
                    "tool_trace": tool_trace[:5],
                }
            )
            state["_tool_trace"] = tool_trace
    except Exception as e:
        trace.finish({"answer_mode": answer_mode}, error=str(e))
        yield _evt({"type": "error", "message": str(e)[:400], "trace_id": trace.trace_id})
        return

    answer = "".join(parts).strip()
    verified = True

    if may_post_fallback and answer_indicates_kb_miss(answer):
        answer_mode = "general"
        fell_back_to_general = True
        meta = []
        ctx = []
        parts = []
        tool_trace = []
        with trace.span("fallback", "llm", inputs={"model": model, "stream": True}) as fb_out:
            try:
                if is_tools_active():
                    yield from stream_general_answer(
                        state=state,
                        client=client,
                        model=model,
                        temperature=temp,
                        max_tokens=mt,
                        history=history,
                        prompt_slots=prompt_slots,
                        parts=parts,
                        tool_trace_out=tool_trace,
                        emit_event=_evt,
                        replay_tokens=_replay_tokens,
                        emit_tokens=True,
                    )
                else:
                    system = augment_system_with_summary(
                        general_system_prompt(slots=prompt_slots),
                        rolling_summary,
                    )
                    user_content = general_user_content(
                        state["question"],
                        contexts=ctx if hybrid and ctx else None,
                    )
                    messages = build_llm_messages(system=system, history=history, user_content=user_content)
                    gen_kw = _gen_kw(model, messages, temp, mt)
                    yield from _stream_tokens(client, gen_kw, parts, emit=True)
                answer = "".join(parts).strip()
                fb_out.update({"answer_len": len(answer), "tool_trace": tool_trace[:5]})
                state["_tool_trace"] = tool_trace
            except Exception:
                pass
    elif may_post_fallback:
        yield from _replay_tokens(parts)

    if answer_mode == "kb" and bool(mem.get("stream_verifier_enabled", False)):
        runtime = {
            "llm_api_key": api_key,
            "llm_api_base": api_base,
            "chat_model": model,
            "llm_temperature_verifier": state.get("llm_temperature_verifier"),
            "llm_max_tokens_verifier": state.get("llm_max_tokens_verifier"),
            "llm_extra_headers": state.get("llm_extra_headers"),
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

    attach = should_attach_citations(
        answer_mode=answer_mode,
        answer=answer,
        contexts_meta=meta,
    )
    cite_kw = {
        "max_sources": int(mem.get("citation_max_sources") or 2),
        "min_relative_score": float(mem.get("citation_min_relative_score") or 0.75),
    }
    sources, source_refs = build_source_citations(meta, **cite_kw) if attach else ([], [])
    full_answer = answer

    done_payload = {
        "type": "done",
        "answer": full_answer,
        "rewritten_query": rewritten,
        "sources": sources if verified else [],
        "source_refs": source_refs if verified else [],
        "answer_mode": answer_mode,
        "verified": verified,
        "trace_id": trace.trace_id,
        "tool_trace": state.get("_tool_trace") or [],
        "topic_shift": bool(state.get("topic_shift")),
        "retrieval_query": state.get("retrieval_query") or state["question"],
        "routing_model": state.get("routing_model"),
        "chat_routing_tier": (mem.get("chat_routing_tier") if mem else "balanced"),
        "condense_used_llm": bool((state.get("turn_meta") or {}).get("condense_used_llm")),
    }
    trace.finish(
        {
            "answer_mode": answer_mode,
            "verified": verified,
            "source_count": len(sources),
            "kb_fallback": fell_back_to_general,
            "trace_id": trace.trace_id,
        },
        error=trace_err,
    )
    yield _evt(done_payload)


def _llm_client(
    state: dict[str, Any],
    api_key: str,
    api_base: str,
) -> tuple[OpenAI, str, float, int | None]:
    headers = state.get("llm_extra_headers")
    client_kw: dict[str, Any] = {"api_key": api_key, "base_url": api_base}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    client = OpenAI(**client_kw)
    model = state.get("chat_model") or settings.openai_chat_model
    temp = float(state.get("llm_temperature_answer") if state.get("llm_temperature_answer") is not None else 0.2)
    mt = state.get("llm_max_tokens_answer")
    mt_int = int(mt) if mt is not None else None
    return client, model, temp, mt_int


def _gen_kw(
    model: str,
    messages: list[dict[str, Any]],
    temp: float,
    max_tokens: int | None,
) -> dict[str, Any]:
    kw: dict[str, Any] = {"model": model, "messages": messages, "temperature": temp, "stream": True}
    if max_tokens is not None:
        kw["max_tokens"] = max_tokens
    return kw


def _stream_tokens(
    client: OpenAI,
    kw: dict[str, Any],
    parts: list[str],
    *,
    emit: bool = True,
) -> Iterator[str]:
    stream = client.chat.completions.create(**kw)
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if not delta:
            continue
        parts.append(delta)
        if emit:
            yield _evt({"type": "token", "content": delta})


def _replay_tokens(parts: list[str]) -> Iterator[str]:
    for delta in parts:
        yield _evt({"type": "token", "content": delta})


def _evt(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
