"""Feedback stats API for Admin dashboard."""

import pytest
from fastapi.testclient import TestClient

from config import settings
from feedback_loop.store import init_feedback_db, insert_feedback, save_triage_result


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "data_feedback_path", tmp_path / "feedback.jsonl")
    monkeypatch.setattr(settings, "chat_trace_path", tmp_path / "trace.jsonl")
    init_feedback_db()

    from api.main import app

    with TestClient(app) as c:
        yield c


def test_feedback_stats_summary(client: TestClient):
    insert_feedback(user_id="u1", rating=1)
    fid = insert_feedback(user_id="u1", rating=0, question="x")
    save_triage_result(
        fid,
        issue_type="retrieval_miss",
        severity="high",
        human_review_required=True,
        summary="test",
    )

    r = client.get("/admin/feedback/stats", params={"since_days": 7})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert body["positive"] >= 1
    assert body["negative"] >= 1
    assert any(row["issue_type"] == "retrieval_miss" for row in body["by_issue_type"])
