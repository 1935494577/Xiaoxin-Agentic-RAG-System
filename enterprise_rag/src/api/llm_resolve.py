"""Resolve OpenAI-compatible LLM connection for a chat request (env vs model profile)."""

from __future__ import annotations

from typing import Any

from api.model_profile_store import effective_api_base, get_default_profile_id, get_profile_raw
from api.schemas import ChatRequest
from config import settings


def resolve_llm_runtime(req: ChatRequest) -> dict[str, Any]:
    """
    Returns keys merged into AgentState: llm_api_base, llm_api_key, chat_model,
    llm_extra_headers, llm_temperature_answer, llm_temperature_verifier,
    llm_max_tokens_rewrite, llm_max_tokens_answer, llm_max_tokens_verifier.
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

    ta = 0.2 if req.temperature is None else float(req.temperature)
    tv = 0.0 if req.verifier_temperature is None else float(req.verifier_temperature)
    trw = 128 if req.max_tokens_rewrite is None else int(req.max_tokens_rewrite)
    tans = req.max_tokens_answer
    tver = req.max_tokens_verifier

    return {
        "llm_api_base": api_base,
        "llm_api_key": api_key,
        "chat_model": model or settings.openai_chat_model,
        "llm_extra_headers": extra,
        "llm_temperature_answer": ta,
        "llm_temperature_verifier": tv,
        "llm_max_tokens_rewrite": trw,
        "llm_max_tokens_answer": tans,
        "llm_max_tokens_verifier": tver,
    }
