"""Feedback tenant isolation via API (Sprint E1/E2)."""

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


def test_feedback_stored_under_request_tenant(client: TestClient):
    r = client.post(
        "/feedback",
        json={"user_id": "u1", "rating": 1},
        headers={"X-Tenant-ID": "tenant-a"},
    )
    assert r.status_code == 200
    fid = r.json()["id"]

    listed, _ = __import__("feedback_loop.store", fromlist=["list_feedback"]).list_feedback(
        tenant_id="tenant-a"
    )
    assert any(row["id"] == fid for row in listed)

    other, total = __import__("feedback_loop.store", fromlist=["list_feedback"]).list_feedback(
        tenant_id="internal"
    )
    assert total == 0
    assert not any(row["id"] == fid for row in other)


def test_admin_list_scoped_to_tenant(client: TestClient):
    client.post(
        "/feedback",
        json={"user_id": "u1", "rating": 0},
        headers={"X-Tenant-ID": "tenant-b"},
    )
    client.post("/feedback", json={"user_id": "u2", "rating": 1})

    r = client.get("/admin/feedback", headers={"X-Tenant-ID": "tenant-b"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["tenant_id"] == "tenant-b"
