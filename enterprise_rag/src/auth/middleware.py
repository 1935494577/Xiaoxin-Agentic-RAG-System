"""Session token authentication middleware."""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from auth.service import STATE_KEY, resolve_session
from auth.im_internal import resolve_im_internal_user
from security.department_features import FULL_ACCESS_DEPARTMENT

AUTH_PUBLIC_PREFIXES = (
    "/health",
    "/auth/login",
    "/favicon.ico",
)
AUTH_PUBLIC_EXACT = {"/", "/openapi.json", "/docs", "/redoc", "/config/nav", "/config/public"}


def _bearer_token(request: Request) -> str:
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (request.headers.get("x-session-token") or "").strip()


def _is_public_path(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    p = path.split("?", 1)[0].rstrip("/") or "/"
    if p in AUTH_PUBLIC_EXACT:
        return True
    return any(p == pref or p.startswith(pref + "/") for pref in AUTH_PUBLIC_PREFIXES)


def get_auth_user(request: Request) -> dict | None:
    user = getattr(request.state, STATE_KEY, None)
    return user if isinstance(user, dict) else None


def auth_department(request: Request) -> str:
    user = get_auth_user(request)
    if user:
        return str(user.get("department") or "")
    from security.department_features import normalize_department

    return normalize_department(request.headers.get("x-user-department"))


class SessionAuthMiddleware(BaseHTTPMiddleware):
    """Require valid session for API routes; attach auth user to request.state."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method.upper()
        token = _bearer_token(request)

        if _is_public_path(path, method):
            user = resolve_session(token)
            if user:
                setattr(request.state, STATE_KEY, user)
            return await call_next(request)

        im_user = resolve_im_internal_user(request)
        if im_user:
            setattr(request.state, STATE_KEY, im_user)
            role = "admin" if im_user.get("department") == FULL_ACCESS_DEPARTMENT else "operator"
            setattr(request.state, "admin_role", role)
            return await call_next(request)

        user = resolve_session(token)
        if not user:
            return JSONResponse({"detail": "未登录或会话已过期，请重新登录"}, status_code=401)

        setattr(request.state, STATE_KEY, user)
        role = "admin" if user.get("department") == FULL_ACCESS_DEPARTMENT else "operator"
        setattr(request.state, "admin_role", role)
        return await call_next(request)
