"""Resolve OpenAI-compatible LLM connection for a chat request (env vs model profile)."""

from __future__ import annotations

from typing import Any

from api.model_profile_store import effective_api_base, get_default_profile_id, get_profile_raw
from api.schemas import ChatRequest
from api.ui_config_store import load_ui_config
from config import settings


def _resolve_routing_model(
    *,
    req: ChatRequest,
    answer_model: str,
    prof: dict[str, Any] | None,
) -> str:
    for candidate in (
        (req.routing_model or "").strip(),
        str(load_ui_config().get("routing_model") or "").strip(),
        str(prof.get("routing_model") or "").strip() if prof else "",
        (settings.openai_routing_model or "").strip(),
        answer_model,
    ):
        if candidate:
            return candidate
    return settings.openai_chat_model


def resolve_llm_runtime(req: ChatRequest) -> dict[str, Any]:
    """
    Returns keys merged into AgentState: llm_api_base, llm_api_key, chat_model,
    routing_model, llm_extra_headers, temperature / max_tokens fields.
    """
    prof = None
    if not req.force_env_llm:
        pid = (req.model_profile_id or "").strip() or None
        if not pid:
            pid = get_default_profile_id()
        prof = get_profile_raw(pid) if pid else None

    if prof:
        api_key = str(prof.get("api_key") or "")
        api_base = effective_api_base(prof)
        model = (
            (req.chat_model or "").strip()
            or str(prof.get("default_model") or "").strip()
            or settings.openai_chat_model
        )
        extra = prof.get("extra_headers") or {}
        if not isinstance(extra, dict):
            extra = {}
    else:
        api_key = settings.openai_api_key
        api_base = settings.openai_api_base.rstrip("/")
        model = (req.chat_model or "").strip() or settings.openai_chat_model
        extra = {}

    answer_model = model or settings.openai_chat_model
    routing_model = _resolve_routing_model(req=req, answer_model=answer_model, prof=prof)

    ta = 0.2 if req.temperature is None else float(req.temperature)
    tv = 0.0 if req.verifier_temperature is None else float(req.verifier_temperature)
    trw = 128 if req.max_tokens_rewrite is None else int(req.max_tokens_rewrite)
    tans = req.max_tokens_answer
    tver = req.max_tokens_verifier

    return {
        "llm_api_base": api_base,
        "llm_api_key": api_key,
        "chat_model": answer_model,
        "routing_model": routing_model,
        "llm_extra_headers": extra,
        "llm_temperature_answer": ta,
        "llm_temperature_verifier": tv,
        "llm_max_tokens_rewrite": trw,
        "llm_max_tokens_answer": tans,
        "llm_max_tokens_verifier": tver,
    }
