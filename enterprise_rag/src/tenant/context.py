"""Tenant context for multi-tenant readiness (Sprint E1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

DEFAULT_TENANT = "internal"
TENANT_HEADER = "x-tenant-id"
STATE_KEY = "tenant_context"


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str = DEFAULT_TENANT


def normalize_tenant_id(raw: str | None) -> str:
    tid = (raw or "").strip()
    return tid or DEFAULT_TENANT


def get_tenant_context(request: Request) -> TenantContext:
    ctx = getattr(request.state, STATE_KEY, None)
    if isinstance(ctx, TenantContext):
        return ctx
    return TenantContext()


def get_tenant_id(request: Request) -> str:
    return get_tenant_context(request).tenant_id


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Attach tenant_id from X-Tenant-ID header; default internal (single-tenant unchanged)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id = normalize_tenant_id(request.headers.get(TENANT_HEADER))
        setattr(request.state, STATE_KEY, TenantContext(tenant_id=tenant_id))
        return await call_next(request)
