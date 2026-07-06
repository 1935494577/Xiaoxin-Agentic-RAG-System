"""Jnao admin gate for Jnao gateway routes."""

from __future__ import annotations

from fastapi import HTTPException, Request

from auth.middleware import auth_department, get_auth_user


async def require_admin_user(request: Request, detail: str = "Admin privileges required.") -> None:
    user = get_auth_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    dept = auth_department(request) or ""
    if dept == "技术部":
        return
    raise HTTPException(status_code=403, detail=detail)
