"""Resolve authenticated user for config layering."""

from __future__ import annotations

from starlette.requests import Request

from auth.middleware import get_auth_user
from security.department_features import FULL_ACCESS_DEPARTMENT


def resolve_config_actor(request: Request) -> tuple[str | None, bool]:
    """Return (user_id, is_platform_admin). Anonymous callers get (None, False)."""
    auth = get_auth_user(request)
    if not auth:
        return None, False
    is_admin = str(auth.get("department") or "") == FULL_ACCESS_DEPARTMENT
    return str(auth.get("id") or "").strip() or None, is_admin
