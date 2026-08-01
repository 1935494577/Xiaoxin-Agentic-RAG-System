"""Chat turn preparation and assistant runtime resolution."""

from __future__ import annotations

from typing import Any

from agent.conversation.prepare import prepare_turn
from agent.conversation_context import resolve_chat_history
from api.chat_memory import chat_memory_settings
from api.chat_routing import apply_routing_tier
from api.routing_mode import apply_hybrid_expert_memory
from api.schemas import ChatRequest
from api.ui_config_store import load_ui_config
from api.chat_session_store import clear_rolling_summary, get_rolling_summary


def resolve_request_history(req: ChatRequest, mem: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    mem = mem or chat_memory_settings()
    req_hist = [h.model_dump() for h in req.history] if req.history else None
    return resolve_chat_history(
        request_history=req_hist,
        user_id=req.user_id,
        session_id=req.session_id,
        max_turns=int(mem.get("max_history_turns", 6)),
        max_chars=int(mem.get("max_history_chars", 6000)),
        long_term_enabled=bool(mem.get("long_term_memory_enabled", True)),
    )


def prepare_chat_turn(
    req: ChatRequest,
    mem: dict[str, Any],
    runtime: dict[str, Any],
):
    raw_history: list[dict[str, Any]] = []
    rolling_summary = ""
    if req.reset_context:
        if req.session_id:
            clear_rolling_summary(req.session_id, req.user_id)
    else:
        raw_history = resolve_request_history(req, mem)
        if req.session_id and bool(mem.get("rolling_summary_enabled", True)):
            rolling_summary = get_rolling_summary(req.session_id, req.user_id)

    return prepare_turn(
        message=req.message,
        history=raw_history,
        memory_config=mem,
        llm_runtime=runtime,
        max_tokens_condense=req.max_tokens_rewrite,
        rolling_summary=rolling_summary,
        reset_context=bool(req.reset_context),
    )


def resolve_chat_architecture(
    req: ChatRequest,
    mem: dict[str, Any],
    runtime: dict[str, Any],
    *,
    rag_override: str | None = None,
) -> tuple[str, str, str | None]:
    from agent.architecture_router import resolve_rag_architecture
    from agent.input_modes import resolve_input_mode
    from agent.llm_routing import routing_llm_runtime

    input_mode, doc_task_type = resolve_input_mode(
        input_mode=req.input_mode,
        doc_task_type=req.doc_task_type,
        temp_document_id=req.temp_document_id,
        message=req.message,
    )
    llm_rt = routing_llm_runtime(runtime)
    arch, _ = resolve_rag_architecture(
        req.message,
        department=req.user_department,
        input_mode=input_mode,
        doc_task_type=doc_task_type,
        scenario_tags=req.scenario_tags,
        request_override=rag_override or req.rag_architecture or mem.get("default_rag_architecture") or "auto",
        router_enabled=bool(mem.get("rag_arch_router_enabled", True)),
        llm_fallback=bool(mem.get("rag_arch_llm_fallback", False)),
        llm_runtime=llm_rt,
    )
    return arch, input_mode, doc_task_type


def prepare_assistant_runtime(
    req: ChatRequest,
    base_mem: dict[str, Any],
) -> tuple[Any, bool, bool, dict[str, Any], str | None]:
    from agent.runtime.router import (
        apply_mode_to_memory,
        pick_hybrid_expert_mode,
        pick_rag_architecture_override,
        pick_stream_fast_mode,
        resolve_mode_profile,
    )

    ui = load_ui_config()
    profile = resolve_mode_profile(req.assistant_mode, ui)
    hybrid = pick_hybrid_expert_mode(profile, bool(ui.get("hybrid_expert_mode", False)))
    fast = pick_stream_fast_mode(
        profile,
        req.stream_fast_mode,
        bool(ui.get("stream_fast_mode", True)),
    )
    mem = apply_mode_to_memory(dict(base_mem), profile)
    mem = apply_routing_tier(apply_hybrid_expert_memory(mem, hybrid))
    rag_override = pick_rag_architecture_override(profile, req.rag_architecture)
    return profile, hybrid, fast, mem, rag_override
