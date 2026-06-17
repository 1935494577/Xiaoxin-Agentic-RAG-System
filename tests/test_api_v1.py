"""API v1 route aliases (Sprint E3)."""

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


def test_v1_feedback_post_alias(client: TestClient):
    legacy = client.post("/feedback", json={"user_id": "u1", "rating": 1})
    v1 = client.post("/api/v1/feedback", json={"user_id": "u2", "rating": 0})
    assert legacy.status_code == 200
    assert v1.status_code == 200

    listed = client.get("/api/v1/admin/feedback")
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
