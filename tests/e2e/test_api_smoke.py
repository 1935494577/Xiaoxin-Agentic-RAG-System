"""Minimal API smoke tests (no full app lifespan / heavy deps)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def minimal_app():
    from api.exam_router import router as exam_router

    app = FastAPI()
    app.include_router(exam_router)
    return app


@pytest.fixture()
def app_with_chat(minimal_app):
    from api.chat_router import router as chat_router

    minimal_app.include_router(chat_router)
    return minimal_app


def test_exam_meta_smoke(minimal_app):
    client = TestClient(minimal_app)
    r = client.get("/api/exam/meta")
    assert r.status_code == 200
    assert r.json().get("available") is True


def test_chat_sessions_require_auth(app_with_chat):
    from auth.middleware import SessionAuthMiddleware
    from tenant.context import TenantContextMiddleware

    app = app_with_chat
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(SessionAuthMiddleware)
    client = TestClient(app)
    r = client.get("/chat/sessions")
    assert r.status_code == 401
