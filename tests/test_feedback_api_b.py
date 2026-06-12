"""Feedback API Sprint B endpoints."""

import pytest
from fastapi.testclient import TestClient

from config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "openai_api_key", "")
    from api.main import app

    with TestClient(app) as c:
        yield c


def test_admin_triage_batch(client: TestClient):
    r1 = client.post("/feedback", json={"user_id": "u1", "rating": 0, "question": "x"})
    assert r1.status_code == 200
    r = client.post("/admin/feedback/triage", json={"limit": 10, "use_llm": False})
    assert r.status_code == 200
    body = r.json()
    assert body["processed"] >= 1

    lst = client.get("/admin/feedback")
    item = lst.json()["items"][0]
    assert item["status"] == "triaged"
    assert item["issue_type"]


def test_admin_approve_feedback(client: TestClient):
    client.post("/feedback", json={"user_id": "u1", "rating": 0, "question": "y"})
    client.post("/admin/feedback/triage", json={"use_llm": False})
    fid = client.get("/admin/feedback").json()["items"][0]["id"]
    r = client.post(f"/admin/feedback/{fid}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_feedback_with_correction(client: TestClient):
    r = client.post(
        "/feedback",
        json={
            "user_id": "u1",
            "rating": 0,
            "question": "Q",
            "correction": "引用的制度已废止",
        },
    )
    assert r.status_code == 200
    fid = r.json()["id"]
    detail = client.get(f"/admin/feedback/{fid}").json()
    assert detail["correction"] == "引用的制度已废止"
