"""Trusted IM channel → Main API auth (loopback / API key)."""

from __future__ import annotations

import hmac

from starlette.requests import Request

from config import settings

_IM_CHAT_PATHS = frozenset({"/chat", "/chat/stream"})
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _api_key(request: Request) -> str:
    key = (request.headers.get("x-api-key") or "").strip()
    if key:
        return key
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def resolve_im_internal_user(request: Request) -> dict | None:
    """Return synthetic auth user for trusted IM backend calls."""
    path = request.url.path.rstrip("/") or "/"
    if path not in _IM_CHAT_PATHS:
        return None
    if request.headers.get("X-IM-Internal", "").strip() != "1":
        return None

    secret = (settings.rag_api_secret or "").strip()
    if secret:
        key = _api_key(request)
        if not key or not hmac.compare_digest(key, secret):
            return None
    else:
        client = request.client
        host = (client.host if client else "") or ""
        if host not in _LOOPBACK_HOSTS:
            return None

    user_id = (request.headers.get("X-IM-User-Id") or "").strip()
    if not user_id:
        return None
    department = (request.headers.get("X-IM-User-Department") or "general").strip() or "general"
    return {
        "id": user_id,
        "username": f"im:{user_id[:48]}",
        "department": department,
        "display_name": "IM Channel",
        "is_active": True,
    }
