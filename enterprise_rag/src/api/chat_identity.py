"""Authenticated chat actor binding — never trust client-supplied user_id."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from api.chat_session_store import get_session
from api.schemas import ChatRequest
from auth.middleware import get_auth_user
from tenant.context import get_tenant_id


def memory_for_user(request: Request | None, user_id: str | None) -> dict[str, Any]:
    from account_config.request_auth import resolve_config_actor
    from api.chat_memory import chat_memory_settings

    auth_uid, _ = resolve_config_actor(request) if request else (None, False)
    actor = auth_uid or ((user_id or "").strip() or None)
    return chat_memory_settings(actor)


def current_user_id(request: Request) -> str:
    """Return the authenticated actor for self-service chat endpoints."""
    auth = get_auth_user(request)
    user_id = str(auth.get("id") or "").strip() if auth else ""
    if not user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    return user_id


def authenticated_chat_request(req: ChatRequest, request: Request) -> ChatRequest:
    """Bind chat execution and session state to the authenticated actor."""
    auth = get_auth_user(request) or {}
    user_id = current_user_id(request)
    department = str(auth.get("department") or req.user_department or "general")
    bound = req.model_copy(update={"user_id": user_id, "user_department": department})
    if bound.session_id and not get_session(
        bound.session_id,
        user_id,
        tenant_id=get_tenant_id(request),
    ):
        raise HTTPException(status_code=404, detail="session not found")
    return bound
