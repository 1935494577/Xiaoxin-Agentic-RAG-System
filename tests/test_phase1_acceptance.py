"""Phase 1 total acceptance — feedback isolation & triage workflow."""

from __future__ import annotations

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

    from api.main import app

    with TestClient(app) as c:
        yield c


def test_chat_unaffected_when_feedback_store_fails(client: TestClient, monkeypatch):
    """Feedback Loop 挂掉时 Chat 热路径仍可用（阶段 1 总验收）。"""

    def _boom(**_kwargs):
        raise RuntimeError("feedback db unavailable")

    monkeypatch.setattr("feedback_loop.service.insert_feedback", _boom)

    assert client.get("/health").status_code == 200
    sess = client.post("/chat/sessions", json={"user_id": "u-phase1"})
    assert sess.status_code == 200
    sid = sess.json()["id"]

    listed = client.get("/chat/sessions", params={"user_id": "u-phase1"})
    assert listed.status_code == 200
    assert any(s["id"] == sid for s in listed.json())

    fb = client.post("/feedback", json={"user_id": "u-phase1", "rating": 0})
    assert fb.status_code == 200
    body = fb.json()
    assert body.get("ok") is False
    assert body.get("error")


def test_negative_feedback_visible_after_triage(client: TestClient):
    """👎 → 规则 Triage → Admin Inbox 可见分类（24h SLA 的能力前提）。"""
    post = client.post(
        "/feedback",
        json={
            "user_id": "u-neg",
            "rating": 0,
            "question": "年假有几天？",
            "answer_preview": "不知道",
            "answer_mode": "general",
        },
    )
    assert post.status_code == 200
    assert post.json().get("ok") is True

    triage = client.post(
        "/admin/feedback/triage",
        json={"limit": 10, "use_llm": False, "rating": 0},
        headers={"X-Admin-Role": "operator"},
    )
    assert triage.status_code == 200
    assert triage.json().get("processed", 0) >= 1

    listed = client.get("/admin/feedback", params={"rating": 0, "status": "triaged"})
    assert listed.status_code == 200
    items = listed.json().get("items") or []
    assert len(items) >= 1
    row = items[0]
    assert row.get("issue_type")
    assert row.get("status") == "triaged"
