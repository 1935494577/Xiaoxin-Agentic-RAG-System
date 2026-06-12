"""Feedback submit + async enrichment orchestration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from feedback_loop.store import append_feedback_jsonl, enrich_feedback, get_feedback, insert_feedback
from feedback_loop.trace_loader import load_trace_by_id, snapshot_from_trace

_log = logging.getLogger(__name__)


def resolve_trace_id(trace_id: str | None, message_id: str | None) -> str | None:
    tid = (trace_id or message_id or "").strip()
    return tid or None


def submit_feedback_record(
    *,
    user_id: str,
    rating: int,
    trace_id: str | None = None,
    message_id: str | None = None,
    session_id: str | None = None,
    question: str | None = None,
    answer_preview: str | None = None,
    answer_mode: str | None = None,
    correction: str | None = None,
    tenant_id: str = "internal",
) -> str:
    resolved_trace = resolve_trace_id(trace_id, message_id)
    return insert_feedback(
        user_id=user_id,
        rating=rating,
        tenant_id=tenant_id,
        trace_id=resolved_trace,
        session_id=session_id,
        message_id=message_id,
        question=question,
        answer_preview=answer_preview,
        answer_mode=answer_mode,
        correction=correction,
    )


def enrich_feedback_from_trace(feedback_id: str) -> None:
    """Load trace by feedback.trace_id and merge snapshot fields (background-safe)."""
    try:
        row = get_feedback(feedback_id)
        if not row:
            return
        tid = row.get("trace_id")
        if not tid:
            _export_feedback_row(feedback_id)
            return
        trace = load_trace_by_id(str(tid))
        if not trace:
            _export_feedback_row(feedback_id)
            return
        snap = snapshot_from_trace(trace)
        enrich_feedback(
            feedback_id,
            context_count=snap.get("context_count"),
            sources=snap.get("sources"),
            trace_snapshot=snap.get("trace_snapshot"),
            question=snap.get("question"),
            answer_mode=snap.get("answer_mode"),
        )
        _export_feedback_row(feedback_id)
    except Exception:
        _log.exception("feedback enrichment failed for %s", feedback_id)


def _export_feedback_row(feedback_id: str) -> None:
    row = get_feedback(feedback_id)
    if not row:
        return
    export_row: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "id": row.get("id"),
        "tenant_id": row.get("tenant_id"),
        "user_id": row.get("user_id"),
        "rating": row.get("rating"),
        "trace_id": row.get("trace_id"),
        "session_id": row.get("session_id"),
        "message_id": row.get("message_id"),
        "question": row.get("question"),
        "answer_preview": row.get("answer_preview"),
        "answer_mode": row.get("answer_mode"),
        "correction": row.get("correction"),
        "context_count": row.get("context_count"),
        "status": row.get("status"),
        "issue_type": row.get("issue_type"),
        "severity": row.get("severity"),
        "triage_summary": row.get("triage_summary"),
        "sources": row.get("sources"),
    }
    append_feedback_jsonl(export_row)


def export_all_feedback_jsonl() -> int:
    """Rewrite JSONL from SQLite (admin on-demand export)."""
    from feedback_loop.store import list_feedback

    rows, _ = list_feedback(since_days=None, limit=50, offset=0)
    # paginate full export
    all_rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch, total = list_feedback(since_days=None, limit=50, offset=offset)
        if not batch:
            break
        all_rows.extend(batch)
        offset += len(batch)
        if offset >= total:
            break

    path = __import__("config").settings.data_feedback_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in all_rows:
            export = {
                "ts": row.get("created_at"),
                "id": row.get("id"),
                "tenant_id": row.get("tenant_id"),
                "user_id": row.get("user_id"),
                "rating": row.get("rating"),
                "trace_id": row.get("trace_id"),
                "session_id": row.get("session_id"),
                "message_id": row.get("message_id"),
                "question": row.get("question"),
                "answer_preview": row.get("answer_preview"),
                "answer_mode": row.get("answer_mode"),
                "correction": row.get("correction"),
                "context_count": row.get("context_count"),
                "sources": row.get("sources"),
            }
            f.write(__import__("json").dumps(export, ensure_ascii=False) + "\n")
    return len(all_rows)
