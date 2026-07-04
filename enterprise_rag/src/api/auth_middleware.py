"""Optional API gateway auth + minimal security headers."""

from __future__ import annotations

import hmac
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api.admin_roles import is_admin_api_path
from config import settings


def _client_token(request: Request) -> str:
    x = (request.headers.get("x-api-key") or "").strip()
    if x:
        return x
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def _is_public_path(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    if path == "/health":
        return True
    if path == "/favicon.ico":
        return True
    if path == "/" and method == "GET":
        return True
    if path.startswith("/auth/"):
        return True
    return False


def _secret_for_path(path: str) -> str:
    admin_secret = (settings.rag_admin_api_secret or "").strip()
    if is_admin_api_path(path) and admin_secret:
        return admin_secret
    return (settings.rag_api_secret or "").strip()


class APIAuthMiddleware(BaseHTTPMiddleware):
    """若配置 RAG_API_SECRET，则除白名单外需携带 X-API-Key 或 Authorization: Bearer。

    管理端路径在配置 RAG_ADMIN_API_SECRET 时须使用独立密钥（Sprint F3）。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        secret = _secret_for_path(request.url.path)
        if not secret or _is_public_path(request.url.path, request.method):
            return await call_next(request)
        got = _client_token(request)
        if not got or not hmac.compare_digest(got, secret):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """降低浏览器侧常见风险（非替代 HTTPS）。"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if settings.enable_hsts:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return resp
