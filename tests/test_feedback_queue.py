"""Feedback queue state machine (Sprint B)."""

import pytest

from config import settings
from feedback_loop.queue import (
    InvalidTransitionError,
    approve_feedback,
    reject_feedback,
    transition_status,
)
from feedback_loop.store import get_feedback, init_feedback_db, insert_feedback, save_triage_result


@pytest.fixture()
def feedback_db(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    init_feedback_db()
    return db


def _pending_id() -> str:
    return insert_feedback(user_id="u1", rating=0, question="Q")


def test_pending_to_triaged(feedback_db):
    fid = _pending_id()
    save_triage_result(
        fid,
        issue_type="retrieval_miss",
        severity="high",
        summary="miss",
        human_review_required=True,
    )
    row = get_feedback(fid)
    assert row["status"] == "triaged"
    assert row["issue_type"] == "retrieval_miss"


def test_triaged_to_approved(feedback_db):
    fid = _pending_id()
    save_triage_result(
        fid,
        issue_type="hallucination",
        severity="medium",
        summary="x",
        human_review_required=True,
    )
    approve_feedback(fid)
    assert get_feedback(fid)["status"] == "approved"


def test_triaged_to_rejected(feedback_db):
    fid = _pending_id()
    save_triage_result(
        fid,
        issue_type="tone",
        severity="low",
        summary="x",
        human_review_required=False,
    )
    reject_feedback(fid)
    assert get_feedback(fid)["status"] == "rejected"


def test_invalid_transition_raises(feedback_db):
    fid = _pending_id()
    with pytest.raises(InvalidTransitionError):
        transition_status(fid, "approved")


def test_cannot_reject_pending(feedback_db):
    fid = _pending_id()
    with pytest.raises(InvalidTransitionError):
        reject_feedback(fid)
