"""Feedback workflow state machine."""

from __future__ import annotations

from feedback_loop.issue_types import STATUSES
from feedback_loop.store import get_feedback, set_feedback_status

ALLOWED: dict[str, set[str]] = {
    "pending": {"triaged"},
    "triaged": {"approved", "rejected"},
    "approved": {"applied"},
    "applied": {"evaluated"},
    "rejected": set(),
    "evaluated": set(),
}


class InvalidTransitionError(ValueError):
    pass


def can_transition(current: str, target: str) -> bool:
    cur = (current or "pending").strip()
    tgt = target.strip()
    return tgt in ALLOWED.get(cur, set())


def transition_status(feedback_id: str, target: str) -> dict:
    row = get_feedback(feedback_id)
    if not row:
        raise KeyError("feedback not found")
    current = str(row.get("status") or "pending")
    tgt = target.strip()
    if tgt not in STATUSES:
        raise ValueError(f"invalid status: {tgt}")
    if not can_transition(current, tgt):
        raise InvalidTransitionError(f"cannot transition {current} -> {tgt}")
    if not set_feedback_status(feedback_id, tgt):
        raise KeyError("feedback not found")
    updated = get_feedback(feedback_id)
    assert updated is not None
    return updated


def approve_feedback(feedback_id: str) -> dict:
    return transition_status(feedback_id, "approved")


def reject_feedback(feedback_id: str) -> dict:
    return transition_status(feedback_id, "rejected")
