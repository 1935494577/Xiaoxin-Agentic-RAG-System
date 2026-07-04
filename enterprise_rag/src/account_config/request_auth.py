"""Resolve authenticated user for config layering."""

from __future__ import annotations

from starlette.requests import Request

from auth.middleware import get_auth_user
from config import settings


def can_write_platform_config(auth: dict | None) -> bool:
    """Only the designated platform writer (default tech1) may persist global config files."""
    if not auth:
        return False
    writer = (settings.platform_config_writer_username or "tech1").strip()
    return str(auth.get("username") or "").strip() == writer


def resolve_config_actor(request: Request) -> tuple[str | None, bool]:
    """Return (user_id, can_write_platform). Anonymous callers get (None, False)."""
    auth = get_auth_user(request)
    if not auth:
        return None, False
    user_id = str(auth.get("id") or "").strip() or None
    return user_id, can_write_platform_config(auth)
