"""Feedback SQLite store (Sprint A)."""

import json
import time

import pytest

from config import settings
from feedback_loop.store import (
    enrich_feedback,
    get_feedback,
    init_feedback_db,
    insert_feedback,
    list_feedback,
)
from feedback_loop.trace_loader import load_trace_by_id


@pytest.fixture()
def feedback_db(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    trace = tmp_path / "chat_trace.jsonl"
    jsonl = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "chat_trace_path", trace)
    monkeypatch.setattr(settings, "data_feedback_path", jsonl)
    init_feedback_db()
    return db


def test_insert_and_list_feedback(feedback_db):
    fid = insert_feedback(
        user_id="u1",
        rating=0,
        trace_id="trace-abc",
        session_id="sess-1",
        question="年假几天？",
        answer_preview="根据制度…",
        answer_mode="kb",
    )
    assert fid

    rows, total = list_feedback(limit=10)
    assert total == 1
    assert rows[0]["id"] == fid
    assert rows[0]["trace_id"] == "trace-abc"
    assert rows[0]["rating"] == 0
    assert rows[0]["tenant_id"] == "internal"


def test_list_feedback_filters(feedback_db):
    insert_feedback(user_id="u1", rating=1, trace_id="t1")
    insert_feedback(user_id="u2", rating=0, trace_id="t2")
    insert_feedback(user_id="u1", rating=0, trace_id="t3")

    rows, total = list_feedback(user_id="u1", rating=0)
    assert total == 1
    assert rows[0]["trace_id"] == "t3"

    rows2, total2 = list_feedback(trace_id="t2")
    assert total2 == 1
    assert rows2[0]["user_id"] == "u2"


def test_enrich_feedback_merges_snapshot(feedback_db):
    fid = insert_feedback(user_id="u1", rating=0, trace_id="t-enrich")
    enrich_feedback(
        fid,
        context_count=3,
        sources=["policy.pdf", "hr.docx"],
        trace_snapshot={"trace_id": "t-enrich", "spans": []},
    )
    row = get_feedback(fid)
    assert row is not None
    assert row["context_count"] == 3
    assert row["sources"] == ["policy.pdf", "hr.docx"]
    assert row["trace_snapshot"]["trace_id"] == "t-enrich"


def test_load_trace_by_id_from_jsonl(tmp_path, monkeypatch):
    trace_path = tmp_path / "traces.jsonl"
    monkeypatch.setattr(settings, "chat_trace_path", trace_path)
    rec = {
        "trace_id": "abc123",
        "question": "测试",
        "spans": [{"name": "retrieve", "output": {"context_count": 2, "contexts_meta": [{"source": "a.txt"}]}}],
    }
    trace_path.write_text(json.dumps({"trace_id": "other"}) + "\n" + json.dumps(rec) + "\n", encoding="utf-8")

    loaded = load_trace_by_id("abc123")
    assert loaded is not None
    assert loaded["question"] == "测试"
    assert load_trace_by_id("missing") is None


def test_list_feedback_since_days(feedback_db):
    fid = insert_feedback(user_id="u1", rating=1)
    row = get_feedback(fid)
    assert row is not None

    rows, total = list_feedback(since_days=7)
    assert total == 1

    # Artificially old created_at
    from feedback_loop import store as store_mod

    with store_mod._lock:
        conn = store_mod._connect()
        try:
            conn.execute(
                "UPDATE feedback_events SET created_at = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", fid),
            )
            conn.commit()
        finally:
            conn.close()

    rows2, total2 = list_feedback(since_days=7)
    assert total2 == 0
