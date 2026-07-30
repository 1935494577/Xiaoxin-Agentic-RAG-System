"""Reuse project .env / default model profile for exam paper routing (same as Chat)."""

from __future__ import annotations

from typing import Any

from config import settings


def _ensure_openai_compatible_base(api_base: str) -> str:
    """DeepSeek and many gateways expect .../v1 for the OpenAI SDK."""
    base = (api_base or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/v1") or base.endswith("/v1beta"):
        return base
    # api.deepseek.com → api.deepseek.com/v1
    if "deepseek.com" in base.lower() or base.count("/") <= 2:
        return f"{base}/v1"
    return base


def resolve_exam_llm_runtime() -> dict[str, Any]:
    """
    Resolve API base / key / model for exam routing.

    Priority (aligned with Chat):
    1. Default model profile (Admin 模型页) if configured with a key
    2. Else ``.env``: OPENAI_API_BASE / OPENAI_API_KEY / OPENAI_CHAT_MODEL
       (routing prefers OPENAI_ROUTING_MODEL when set, else chat model)
    """
    api_key = ""
    api_base = ""
    chat_model = ""
    routing_model = ""
    extra: dict[str, str] = {}
    source = "env"

    try:
        from api.model_profile_store import effective_api_base, get_default_profile_id, get_profile_raw

        pid = get_default_profile_id()
        prof = get_profile_raw(pid) if pid else None
        if prof and str(prof.get("api_key") or "").strip():
            api_key = str(prof.get("api_key") or "").strip()
            api_base = effective_api_base(prof)
            chat_model = str(prof.get("default_model") or "").strip()
            routing_model = str(prof.get("routing_model") or "").strip()
            hdr = prof.get("extra_headers") or {}
            if isinstance(hdr, dict):
                extra = {str(k): str(v) for k, v in hdr.items()}
            source = f"profile:{pid}"
    except Exception:
        pass

    if not api_key:
        api_key = (settings.openai_api_key or "").strip()
        api_base = (settings.openai_api_base or "").strip()
        chat_model = (settings.openai_chat_model or "").strip()
        routing_model = (settings.openai_routing_model or "").strip()
        source = "env"

    chat_model = chat_model or (settings.openai_chat_model or "").strip() or "deepseek-v4-flash"
    # Exam routing is a preprocessor-style task → prefer routing_model, else chat model
    model = (routing_model or settings.openai_routing_model or "").strip() or chat_model
    api_base = _ensure_openai_compatible_base(api_base or settings.openai_api_base)

    return {
        "llm_api_base": api_base,
        "llm_api_key": api_key,
        "chat_model": chat_model,
        "routing_model": model,
        "model": model,
        "llm_extra_headers": extra,
        "source": source,
    }


def build_openai_client(*, timeout_sec: float = 45.0) -> tuple[Any, dict[str, Any]] | tuple[None, dict[str, Any]]:
    """Return (OpenAI client, runtime) or (None, runtime) if key missing."""
    from openai import OpenAI

    rt = resolve_exam_llm_runtime()
    key = str(rt.get("llm_api_key") or "").strip()
    if not key:
        return None, rt
    base = str(rt.get("llm_api_base") or "").strip() or None
    headers = rt.get("llm_extra_headers") or {}
    client_kw: dict[str, Any] = {"api_key": key, "base_url": base, "timeout": timeout_sec}
    if isinstance(headers, dict) and headers:
        client_kw["default_headers"] = headers
    return OpenAI(**client_kw), rt
