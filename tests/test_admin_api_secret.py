"""Separate admin API secret (Sprint F3)."""

import pytest
from fastapi.testclient import TestClient

from config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    jsonl = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "data_feedback_path", jsonl)
    monkeypatch.setattr(settings, "chat_trace_path", tmp_path / "trace.jsonl")

    from api.main import app

    with TestClient(app) as c:
        yield c


def test_admin_paths_require_admin_secret_when_configured(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "rag_api_secret", "chat-key", raising=False)
    monkeypatch.setattr(settings, "rag_admin_api_secret", "admin-key", raising=False)
    try:
        assert client.get("/admin/feedback").status_code == 401
        assert client.get("/admin/feedback", headers={"X-API-Key": "chat-key"}).status_code == 401
        assert client.get("/admin/feedback", headers={"X-API-Key": "admin-key"}).status_code == 200
        assert client.get("/config/public", headers={"X-API-Key": "chat-key"}).status_code == 200
    finally:
        monkeypatch.setattr(settings, "rag_api_secret", "", raising=False)
        monkeypatch.setattr(settings, "rag_admin_api_secret", "", raising=False)
