"""Middleware: enforce department feature access from session or X-User-Department."""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from auth.middleware import auth_department, get_auth_user
from security.department_features import can_access_feature, feature_for_request, normalize_department


class DepartmentFeatureMiddleware(BaseHTTPMiddleware):
    """When X-User-Department is set, restrict admin APIs by department."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        department = auth_department(request)
        feature = feature_for_request(request.method, request.url.path)
        if feature and not can_access_feature(department or None, feature):
            return JSONResponse(
                {
                    "detail": f"当前部门无权访问该功能（{feature}）",
                    "feature": feature,
                    "department": department,
                },
                status_code=403,
            )
        return await call_next(request)
