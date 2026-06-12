"""Feedback LLM / rule triage (Sprint B)."""

import pytest

from config import settings
from feedback_loop.store import get_feedback, init_feedback_db, insert_feedback
from feedback_loop.issue_types import issue_type_label
from feedback_loop.triage import rule_based_triage, run_triage_batch


@pytest.fixture()
def feedback_db(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    init_feedback_db()
    return db


def test_rule_triage_retrieval_miss(feedback_db):
    fid = insert_feedback(user_id="u1", rating=0, question="年假？")
    from feedback_loop.store import enrich_feedback

    enrich_feedback(fid, context_count=0, sources=[])
    out = rule_based_triage(get_feedback(fid) or {})
    assert out["issue_type"] == "retrieval_miss"
    assert out["severity"] in ("high", "medium")


def test_rule_triage_positive_ok(feedback_db):
    fid = insert_feedback(user_id="u1", rating=1, question="谢谢")
    out = rule_based_triage(get_feedback(fid) or {})
    assert out["issue_type"] == "ok"
    assert out["human_review_required"] is False


def test_rule_triage_uses_correction_hint(feedback_db):
    fid = insert_feedback(
        user_id="u1",
        rating=0,
        question="报销流程",
        correction="文档已过期，应按 2025 版制度",
        answer_preview="按 2020 年…",
    )
    from feedback_loop.store import enrich_feedback

    enrich_feedback(fid, context_count=2, sources=["old.pdf"])
    out = rule_based_triage(get_feedback(fid) or {})
    assert out["issue_type"] in ("stale_doc", "hallucination", "prompt")


def test_run_triage_batch_without_llm(feedback_db, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    f1 = insert_feedback(user_id="u1", rating=0, question="a")
    f2 = insert_feedback(user_id="u1", rating=1, question="b")
    result = run_triage_batch(limit=10, use_llm=False)
    assert result["processed"] == 2
    assert get_feedback(f1)["status"] == "triaged"
    assert get_feedback(f2)["status"] == "triaged"


def test_llm_triage_parsed(monkeypatch, feedback_db):
    fid = insert_feedback(user_id="u1", rating=0, question="制度", correction="答案编造了")
    from feedback_loop import triage as triage_mod

    def fake_llm(_row, **_kw):
        return {
            "issue_type": "hallucination",
            "severity": "high",
            "human_review_required": True,
            "summary": "与资料不符",
            "suggested_actions": [{"action": "add_to_golden", "confidence": 0.9}],
        }

    monkeypatch.setattr(triage_mod, "llm_triage", fake_llm)
    triage_mod.run_triage_one(fid, use_llm=True)
    row = get_feedback(fid)
    assert row["issue_type"] == "hallucination"
    assert row["status"] == "triaged"


def test_issue_type_labels():
    assert issue_type_label("retrieval_miss") == "检索未命中"
