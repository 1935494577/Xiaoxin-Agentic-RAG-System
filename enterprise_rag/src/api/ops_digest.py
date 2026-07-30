"""Lightweight ops digest for Admin (today / recent window)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from api.token_usage_store import _db_path, init_token_usage_db, _lock


def _utc_day_start(days_ago: int = 0) -> str:
    now = datetime.now(timezone.utc)
    day = (now - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
    return day.isoformat()


def token_usage_since(*, since_iso: str) -> dict[str, int]:
    init_token_usage_db()
    path = _db_path()
    if not path.is_file():
        return {"total_tokens": 0, "total_calls": 0, "total_input_tokens": 0, "total_output_tokens": 0}
    with _lock:
        conn = sqlite3.connect(path)
        try:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(total_tokens), 0),
                    COALESCE(SUM(prompt_tokens), 0),
                    COALESCE(SUM(completion_tokens), 0),
                    COUNT(*)
                FROM llm_calls
                WHERE created_at >= ?
                """,
                (since_iso,),
            ).fetchone()
        finally:
            conn.close()
    return {
        "total_tokens": int(row[0] or 0),
        "total_input_tokens": int(row[1] or 0),
        "total_output_tokens": int(row[2] or 0),
        "total_calls": int(row[3] or 0),
    }


def build_ops_digest(*, since_days: int = 1) -> dict[str, Any]:
    """Aggregate lightweight KPIs for the last N calendar days (UTC)."""
    days = max(1, min(int(since_days), 30))
    since = _utc_day_start(days - 1)
    tokens = token_usage_since(since_iso=since)
    feedback: dict[str, Any] = {}
    try:
        from feedback_loop.stats import feedback_stats

        feedback = feedback_stats(since_days=days)
    except Exception:
        feedback = {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "pending_triage": 0,
            "by_issue_type": [],
        }

    by_issue = feedback.get("by_issue_type") or []
    retrieval_miss = 0
    for item in by_issue:
        if str(item.get("issue_type") or "") == "retrieval_miss":
            retrieval_miss = int(item.get("count") or 0)
            break

    return {
        "since": since,
        "since_days": days,
        "token_usage": tokens,
        "feedback": {
            "total": int(feedback.get("total") or 0),
            "positive": int(feedback.get("positive") or 0),
            "negative": int(feedback.get("negative") or 0),
            "pending_triage": int(feedback.get("pending_triage") or 0),
            "retrieval_miss": retrieval_miss,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
