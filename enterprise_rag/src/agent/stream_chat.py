"""Retrieve + streaming answer with memory, kb/general routing, optional verifier."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterator

from agent.answer_prompts import (
    general_system_prompt,
    general_user_content,
    kb_system_prompt,
    kb_user_content,
)
from agent.architecture_router import resolve_rag_architecture
from agent.input_modes import resolve_input_mode
from agent.kb_judge import answer_indicates_kb_miss, should_attach_citations, should_use_knowledge_base
from agent.answer_router import resolve_answer_mode
from agent.context_format import build_source_citations
from agent.conversation_context import build_llm_messages
from agent.conversation.rolling_summary import augment_system_with_summary
from agent.llm_routing import routing_llm_runtime
from agent.pipelines.agentic import stream_agentic_answer
from agent.pipelines.classic import run_classic_retrieval, run_graph_retrieval
from agent.pipelines.doc_task import retrieve_for_doc_task
from agent.pipelines.relationship_graph import stream_relationship_graph_turn
from agent.stream_verifier import run_stream_verifier
from agent.tools.runtime.routing import (
    question_needs_agent_tools,
    question_needs_realtime_tools,
    resolve_relationship_graph_query,
    enrich_question_for_fact_correction,
    resolve_web_search_query,
    should_use_relationship_graph_fast_path,
    should_use_web_search_followup,
)
from agent.tools.runtime.stream import is_tools_active, stream_general_answer
from agent.clarify import (
    apply_clarify_choice_to_message,
    build_clarify_event,
    resolve_clarify_choice,
    should_offer_clarify,
)
from agent.chitchat import canned_chitchat_reply, is_chitchat_message
from agent.output_schemas import output_schema_instruction
from graph.prompts import graph_kb_system_extra
from config import settings
from evaluation.stream_tracer import new_stream_tracer
from api.stream_errors import format_stream_error
from openai import OpenAI


def apply_strict_kb_miss_contexts(
    *,
    kb_ok: bool,
    answer_mode: str,
    ctx: list[str],
    meta: list[dict[str, Any]],
    general_fallback_enabled: bool,
) -> tuple[str, list[str], list[dict[str, Any]], bool]:
    """When strict KB judge rejects retrieval, drop weak chunks so they cannot steer the answer.

    Returns (answer_mode, ctx, meta, missed).
    """
    if kb_ok or answer_mode != "kb":
        return answer_mode, ctx, meta, False
    if general_fallback_enabled:
        return "general", [], [], True
    return "kb", [], [], True


def _is_realtime_tool_turn(
    state: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
) -> bool:
    """Realtime / web-search tool turns (DeerFlow-style: regex + confirm follow-ups)."""
    if not is_tools_active():
        return False
    q = str(state.get("question") or "")
    if history and should_use_web_search_followup(q, history):
        return True
    if question_needs_realtime_tools(q):
        return True
    meta = state.get("turn_meta") or {}
    return meta.get("query_intent") == "realtime"


def stream_rag_chat(state: dict[str, Any]) -> Iterator[str]:
    """Yield SSE lines: data: {json}\n\n"""
    # Deterministic exam-bank awareness: do not invent papers from KB / general LLM
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
        logging.getLogger(__name__).exception("exam chat gate failed")
        from exam_bank.chat_exam_gate import exam_gate_failure_response, iter_exam_gate_sse

        for ev in iter_exam_gate_sse(exam_gate_failure_response()):
            yield _evt(ev)
        return

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
    reasoning_mode = str(mem.get("agent_reasoning_mode") or "react")
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

    choice_id = str(state.get("clarify_choice_id") or "").strip()
    if choice_id:
        choice = resolve_clarify_choice(choice_id)
        if choice:
            state["question"] = apply_clarify_choice_to_message(state["question"], choice)
            init_state["question"] = state["question"]
            if choice.get("output_schema_id") and not state.get("output_schema_id"):
                state["output_schema_id"] = choice["output_schema_id"]

    turn_meta = state.get("turn_meta") or {}
    if should_offer_clarify(
        enabled=bool(mem.get("clarify_enabled")),
        skip_clarify=bool(state.get("skip_clarify")),
        clarify_choice_id=choice_id or None,
        rule_confidence=float(turn_meta.get("rule_confidence") or 1.0),
        intent=str(turn_meta.get("query_intent") or "unknown"),
        message=str(state.get("question") or ""),
    ):
        yield _evt(build_clarify_event(channel=state.get("channel")))
        yield _evt(
            {
                "type": "done",
                "answer": "",
                "needs_clarify": True,
                "trace_id": trace.trace_id,
            }
        )
        trace.finish({})
        return

    schema_extra = output_schema_instruction(str(state.get("output_schema_id") or ""))

    # Pure greeting / courtesy: skip retrieval & tools (canned reply, no LLM).
    if is_chitchat_message(str(state.get("question") or "")):
        answer = canned_chitchat_reply(str(state.get("question") or ""))
        if not quiet:
            yield _evt(
                {
                    "type": "status",
                    "phase": "generating",
                    "answer_mode": "general",
                    "rag_architecture": "classic",
                    "chitchat": True,
                    "trace_id": trace.trace_id,
                }
            )
        yield from _replay_tokens([answer])
        done_payload = {
            "type": "done",
            "answer": answer,
            "rewritten_query": state["question"],
            "sources": [],
            "source_refs": [],
            "answer_mode": "general",
            "rag_architecture": "classic",
            "input_mode": "chat",
            "verified": True,
            "trace_id": trace.trace_id,
            "tool_trace": [],
            "graph_viz": None,
            "topic_shift": False,
            "retrieval_query": state["question"],
            "chitchat": True,
        }
        trace.finish({"answer_mode": "general", "chitchat": True, "trace_id": trace.trace_id})
        yield _evt(done_payload)
        return

    if should_use_relationship_graph_fast_path(state["question"], history):
        graph_state = dict(state)
        graph_state["relationship_graph_query"] = resolve_relationship_graph_query(
            state["question"],
            history,
        )
        yield from stream_relationship_graph_turn(graph_state, trace=trace, quiet=quiet, emit=_evt)
        return

    raw_question = str(state["question"] or "")
    web_search_followup = should_use_web_search_followup(raw_question, history)
    realtime_tool_turn = _is_realtime_tool_turn(state, history)
    if realtime_tool_turn:
        state = dict(state)
        state["_realtime_tool_turn"] = True
        state["agent_reasoning_mode"] = "react"
        reasoning_mode = "react"
        if web_search_followup:
            resolved = resolve_web_search_query(raw_question, history)
            state["question"] = resolved
            init_state["question"] = resolved
            state["_web_search_followup"] = True
        else:
            corrected = enrich_question_for_fact_correction(raw_question, history)
            if corrected:
                state["question"] = corrected
                init_state["question"] = corrected
                state["_fact_correction_turn"] = True

    input_mode, doc_task_type = resolve_input_mode(
        input_mode=state.get("input_mode"),
        doc_task_type=state.get("doc_task_type"),
        temp_document_id=state.get("temp_document_id"),
        message=state["question"],
    )
    router_enabled = bool(mem.get("rag_arch_router_enabled", True))
    llm_fallback = bool(mem.get("rag_arch_llm_fallback", False))
    req_override = state.get("rag_architecture") or mem.get("default_rag_architecture") or "auto"
    rag_arch, route_meta = resolve_rag_architecture(
        state["question"],
        department=str(state.get("user_department") or ""),
        input_mode=input_mode,
        doc_task_type=doc_task_type,
        scenario_tags=state.get("scenario_tags"),
        request_override=req_override,
        router_enabled=router_enabled,
        llm_fallback=llm_fallback,
        llm_runtime=llm_runtime,
    )
    state["rag_architecture"] = rag_arch
    state["input_mode"] = input_mode
    state["doc_task_type"] = doc_task_type

    if not quiet:
        yield _evt(
            {
                "type": "status",
                "phase": "routing",
                "rag_architecture": rag_arch,
                "input_mode": input_mode,
                "doc_task_type": doc_task_type,
                "route_meta": route_meta,
                "assistant_mode": state.get("assistant_mode"),
                "trace_id": trace.trace_id,
            }
        )

    use_agentic_pipeline = rag_arch == "agentic" and not realtime_tool_turn

    if not quiet and not use_agentic_pipeline and not realtime_tool_turn:
        qu_meta = (state.get("turn_meta") or {}).get("query_understanding")
        if isinstance(qu_meta, dict) and qu_meta:
            yield _evt(
                {
                    "type": "status",
                    "phase": "query_understanding",
                    "query_understanding": qu_meta,
                    "trace_id": trace.trace_id,
                }
            )
        yield _evt({"type": "status", "phase": "retrieving", "trace_id": trace.trace_id})

    ctx: list[str] = []
    meta: list[dict[str, Any]] = []
    rewritten = state.get("retrieval_query") or state["question"]
    retrieval_meta: dict[str, Any] = dict(state.get("turn_meta") or {})
    retrieval_meta.setdefault(
        "retrieval_mode",
        str((state.get("turn_meta") or {}).get("retrieval_mode") or "hybrid"),
    )

    if use_agentic_pipeline:
        with trace.span(
            "retrieve",
            "agentic",
            inputs={"question": state["question"], "rag_architecture": rag_arch},
        ):
            pass
    elif not realtime_tool_turn:
        try:
            with trace.span(
                "retrieve",
                "retriever",
                inputs={
                    "question": state["question"],
                    "stream_fast_mode": fast,
                    "rag_architecture": rag_arch,
                    "input_mode": input_mode,
                },
            ) as span_out:
                try:
                    if input_mode in ("doc_task", "temp_document"):
                        retrieved = retrieve_for_doc_task(
                            init_state,
                            input_mode=input_mode,
                            doc_task_type=doc_task_type,
                        )
                    elif rag_arch == "graph":
                        retrieved = run_graph_retrieval(init_state)
                    else:
                        retrieved = run_classic_retrieval(init_state)
                except Exception as e:
                    trace_err = str(e)
                    raise
                ctx = retrieved.get("contexts") or []
                meta = retrieved.get("contexts_meta") or []
                rewritten = retrieved.get("rewritten_query") or state["question"]
                if isinstance(retrieved.get("retrieval_meta"), dict):
                    retrieval_meta.update(retrieved["retrieval_meta"])
                span_out.update(
                    {
                        "rewritten_query": rewritten,
                        "context_count": len(ctx),
                        "contexts_meta": meta[:5],
                        "rag_architecture": rag_arch,
                        "retrieval_meta": retrieval_meta,
                    }
                )
            if not quiet and retrieval_meta:
                yield _evt(
                    {
                        "type": "status",
                        "phase": "retrieval_routing",
                        "retrieval_mode": retrieval_meta.get("retrieval_mode"),
                        "paths_used": retrieval_meta.get("paths_used"),
                        "elapsed_ms": retrieval_meta.get("elapsed_ms"),
                        "trace_id": trace.trace_id,
                    }
                )
        except Exception as e:
            trace.finish({}, error=str(e))
            yield _evt({"type": "error", "message": format_stream_error(e), "trace_id": trace.trace_id})
            return

    with trace.span(
        "route",
        "chain",
        inputs={"question": state["question"], "context_count": len(ctx), "rag_architecture": rag_arch},
    ) as route_out:
        if use_agentic_pipeline:
            answer_mode = "general" if hybrid else "kb"
        else:
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
            if realtime_tool_turn and is_tools_active():
                answer_mode = "general"
                route_out["tool_route_override"] = "realtime"
            elif hybrid and is_tools_active() and question_needs_agent_tools(raw_question):
                answer_mode = "general"
                route_out["tool_route_override"] = True
        route_out["answer_mode"] = answer_mode
        route_out["rag_architecture"] = rag_arch

    strict_kb_only = not hybrid
    if strict_kb_only and not use_agentic_pipeline and answer_mode == "kb":
        kb_ok = should_use_knowledge_base(
            state["question"],
            ctx,
            meta,
            kb_min_score=float(mem.get("kb_min_score", 0.55)),
            kb_min_rerank_score=float(mem.get("kb_min_rerank_score", 0.0)),
            kb_llm_judge=bool(mem.get("kb_llm_judge", True)),
            llm_runtime=llm_runtime,
            topic_shift=bool(state.get("topic_shift")),
            kb_llm_judge_always=bool(mem.get("kb_llm_judge_always", False)),
        )
        answer_mode, ctx, meta, missed = apply_strict_kb_miss_contexts(
            kb_ok=kb_ok,
            answer_mode=answer_mode,
            ctx=ctx,
            meta=meta,
            general_fallback_enabled=bool(mem.get("general_fallback_enabled", True)),
        )
        if missed:
            state["_kb_strict_miss"] = True

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
                "rag_architecture": rag_arch,
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
            if use_agentic_pipeline:
                max_turns = int(mem.get("agentic_max_turns") or 6)
                try:
                    yield from stream_agentic_answer(
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
                        max_turns=max_turns,
                    )
                except Exception as e:
                    trace_err = str(e)
                    raise
                agentic_hits = list(state.get("_agentic_hits") or [])
                if agentic_hits:
                    meta = agentic_hits
                    ctx = [str(h.get("text") or "") for h in agentic_hits]
                    answer_mode = "kb"
            elif answer_mode == "kb":
                graph_extra = graph_kb_system_extra() if rag_arch == "graph" else ""
                system = augment_system_with_summary(
                    kb_system_prompt(
                        fast=fast,
                        slots=prompt_slots,
                        reasoning_mode=reasoning_mode,
                        strict_kb_only=strict_kb_only,
                    )
                    + (f"\n\n{graph_extra}" if graph_extra else "")
                    + (f"\n\n{schema_extra}" if schema_extra else ""),
                    rolling_summary,
                )
                user_content = kb_user_content(ctx, state["question"])
                messages = build_llm_messages(system=system, history=history, user_content=user_content)
                kw = _gen_kw(model, messages, temp, mt)
                try:
                    if may_post_fallback:
                        for _ in _stream_tokens(client, kw, parts, emit=False, state=state):
                            pass
                    else:
                        yield from _stream_tokens(client, kw, parts, emit=True, state=state)
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
                    general_system_prompt(slots=prompt_slots, reasoning_mode=reasoning_mode),
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
                        for _ in _stream_tokens(client, kw, parts, emit=False, state=state):
                            pass
                    else:
                        yield from _stream_tokens(client, kw, parts, emit=True, state=state)
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
        yield _evt({"type": "error", "message": format_stream_error(e), "trace_id": trace.trace_id})
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
                        general_system_prompt(slots=prompt_slots, reasoning_mode=reasoning_mode),
                        rolling_summary,
                    )
                    user_content = general_user_content(
                        state["question"],
                        contexts=ctx if hybrid and ctx else None,
                    )
                    messages = build_llm_messages(system=system, history=history, user_content=user_content)
                    gen_kw = _gen_kw(model, messages, temp, mt)
                    yield from _stream_tokens(client, gen_kw, parts, emit=True, state=state)
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
                metering_state=state,
            )
            answer = str(vout.get("answer") or answer)
            verified = bool(vout.get("verified", True))
            ver_out.update({"verified": verified})

    attach = should_attach_citations(
        answer_mode=answer_mode,
        answer=answer,
        contexts_meta=meta,
        kb_min_score=float(mem.get("kb_min_score", 0.55)),
        kb_min_rerank_score=float(mem.get("kb_min_rerank_score", 0.12)),
        topic_shift=bool(state.get("topic_shift")),
    )
    cite_kw = {
        "max_sources": int(mem.get("citation_max_sources") or 2),
        "min_relative_score": float(mem.get("citation_min_relative_score") or 0.75),
    }
    sources, source_refs = build_source_citations(meta, **cite_kw) if attach else ([], [])
    full_answer = answer

    graph_viz_payload = _graph_viz_from_tool_trace(state.get("_tool_trace") or [])

    done_payload = {
        "type": "done",
        "answer": full_answer,
        "rewritten_query": rewritten,
        "sources": sources if verified else [],
        "source_refs": source_refs if verified else [],
        "answer_mode": answer_mode,
        "rag_architecture": rag_arch,
        "input_mode": input_mode,
        "verified": verified,
        "trace_id": trace.trace_id,
        "tool_trace": state.get("_tool_trace") or [],
        "graph_viz": graph_viz_payload,
        "topic_shift": bool(state.get("topic_shift")),
        "retrieval_query": state.get("retrieval_query") or state["question"],
        "routing_model": state.get("routing_model"),
        "chat_routing_tier": (mem.get("chat_routing_tier") if mem else "balanced"),
        "condense_used_llm": bool((state.get("turn_meta") or {}).get("condense_used_llm")),
    }
    trace.finish(
        {
            "answer_mode": answer_mode,
            "rag_architecture": rag_arch,
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
    state: dict[str, Any] | None = None,
    caller: str = "answer",
) -> Iterator[str]:
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
        if not getattr(chunk, "choices", None):
            continue
        delta = chunk.choices[0].delta.content or ""
        if not delta:
            continue
        parts.append(delta)
        if emit:
            yield _evt({"type": "token", "content": delta})
    try:
        from api.token_usage_store import metering_meta_from_state, record_usage_object

        record_usage_object(
            usage,
            model=str(kw.get("model") or ""),
            caller=caller,
            **metering_meta_from_state(state),
        )
    except Exception:
        pass


def _replay_tokens(parts: list[str]) -> Iterator[str]:
    for delta in parts:
        yield _evt({"type": "token", "content": delta})


def _graph_viz_from_tool_trace(tool_trace: list[dict[str, Any]]) -> dict[str, Any] | None:
    from graph.viz import parse_graph_viz_from_tool_output

    for row in reversed(tool_trace):
        if str(row.get("tool") or "") != "show_relationship_graph":
            continue
        out = str(row.get("output") or "")
        viz = parse_graph_viz_from_tool_output(out)
        if viz:
            return viz
    return None


def _evt(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
