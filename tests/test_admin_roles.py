"""Admin role enforcement (Sprint F2)."""

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


def test_viewer_can_list_feedback(client: TestClient):
    client.post("/feedback", json={"user_id": "u1", "rating": 1})
    r = client.get("/admin/feedback", headers={"X-Admin-Role": "viewer"})
    assert r.status_code == 200


def test_viewer_cannot_triage(client: TestClient):
    client.post("/feedback", json={"user_id": "u1", "rating": 0})
    r = client.post(
        "/admin/feedback/triage",
        json={"limit": 5, "use_llm": False},
        headers={"X-Admin-Role": "viewer"},
    )
    assert r.status_code == 403


def test_operator_can_triage(client: TestClient):
    client.post("/feedback", json={"user_id": "u1", "rating": 0})
    r = client.post(
        "/admin/feedback/triage",
        json={"limit": 5, "use_llm": False},
        headers={"X-Admin-Role": "operator"},
    )
    assert r.status_code == 200
