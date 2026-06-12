"""Feedback API (Sprint A)."""

import json

import pytest
from fastapi.testclient import TestClient

from config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    trace = tmp_path / "chat_trace.jsonl"
    jsonl = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "chat_trace_path", trace)
    monkeypatch.setattr(settings, "data_feedback_path", jsonl)

    trace.write_text(
        json.dumps(
            {
                "trace_id": "tr-1",
                "question": "Q from trace",
                "spans": [
                    {
                        "name": "retrieve",
                        "output": {
                            "context_count": 2,
                            "contexts_meta": [{"source": "doc.pdf"}],
                        },
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    from api.main import app

    with TestClient(app) as c:
        yield c


def test_feedback_post_minimal_backward_compatible(client: TestClient):
    r = client.post(
        "/feedback",
        json={"user_id": "u1", "rating": 1, "message_id": "tr-legacy"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["id"]


def test_feedback_post_extended_fields(client: TestClient):
    r = client.post(
        "/feedback",
        json={
            "user_id": "u1",
            "rating": 0,
            "trace_id": "tr-1",
            "session_id": "s1",
            "question": "年假？",
            "answer_preview": "10天",
            "answer_mode": "kb",
        },
    )
    assert r.status_code == 200
    fid = r.json()["id"]

    # Background enrichment runs inline in TestClient
    import time

    time.sleep(0.05)

    detail = client.get(f"/admin/feedback/{fid}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["trace_id"] == "tr-1"
    assert body["context_count"] == 2
    assert "doc.pdf" in body["sources"]


def test_admin_feedback_list_pagination(client: TestClient):
    for i in range(3):
        client.post("/feedback", json={"user_id": "u1", "rating": 1, "trace_id": f"t{i}"})

    r = client.get("/admin/feedback", params={"limit": 2, "offset": 0, "since_days": 7})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2


def test_admin_feedback_export_jsonl(client: TestClient, tmp_path):
    client.post("/feedback", json={"user_id": "u1", "rating": 0, "trace_id": "tx"})
    r = client.post("/admin/feedback/export-jsonl")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert settings.data_feedback_path.is_file()
    lines = settings.data_feedback_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1


def test_admin_feedback_trace_lookup(client: TestClient):
    r = client.get("/admin/feedback/traces/tr-1")
    assert r.status_code == 200
    assert r.json()["trace_id"] == "tr-1"
    assert client.get("/admin/feedback/traces/not-found").status_code == 404
