"""Admin role enforcement for management APIs (Sprint F2)."""

from __future__ import annotations

from typing import Callable, Literal

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

AdminRole = Literal["viewer", "operator", "admin"]
ADMIN_ROLE_HEADER = "x-admin-role"
STATE_KEY = "admin_role"

ROLE_LEVEL: dict[AdminRole, int] = {
    "viewer": 0,
    "operator": 1,
    "admin": 2,
}


def normalize_admin_path(path: str) -> str:
    p = (path or "").split("?", 1)[0].rstrip("/") or "/"
    if p.startswith("/api/v1"):
        p = p[len("/api/v1") :] or "/"
    return p


def is_admin_api_path(path: str) -> bool:
    return normalize_admin_path(path).startswith("/admin/")


def parse_admin_role(raw: str | None) -> AdminRole:
    value = (raw or "").strip().lower()
    if value in ROLE_LEVEL:
        return value  # type: ignore[return-value]
    return "admin"


def required_admin_role(method: str, path: str) -> AdminRole | None:
    p = normalize_admin_path(path)
    if not p.startswith("/admin/"):
        return None
    m = (method or "GET").upper()
    if m == "GET":
        return "viewer"
    if "/config-revisions/" in p and m == "POST" and p.endswith("/rollback"):
        return "admin"
    return "operator"


def get_admin_role(request: Request) -> AdminRole:
    role = getattr(request.state, STATE_KEY, None)
    if isinstance(role, str) and role in ROLE_LEVEL:
        return role  # type: ignore[return-value]
    return parse_admin_role(request.headers.get(ADMIN_ROLE_HEADER))


def role_allows(actual: AdminRole, required: AdminRole) -> bool:
    return ROLE_LEVEL[actual] >= ROLE_LEVEL[required]


class AdminRoleMiddleware(BaseHTTPMiddleware):
    """Restrict /admin/* mutating endpoints by X-Admin-Role (viewer < operator < admin)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        required = required_admin_role(request.method, request.url.path)
        role = parse_admin_role(request.headers.get(ADMIN_ROLE_HEADER))
        setattr(request.state, STATE_KEY, role)
        if required and not role_allows(role, required):
            return JSONResponse(
                {
                    "detail": f"需要 {required} 及以上权限",
                    "required_role": required,
                    "role": role,
                },
                status_code=403,
            )
        return await call_next(request)
