"""Feedback aggregate stats for Admin dashboard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from feedback_loop.store import DEFAULT_TENANT, _connect, _lock


def feedback_stats(*, tenant_id: str = DEFAULT_TENANT, since_days: int = 7) -> dict[str, Any]:
    tid = (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    days = max(1, min(int(since_days), 365))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with _lock:
        conn = _connect()
        try:
            total = int(
                conn.execute(
                    "SELECT COUNT(*) FROM feedback_events WHERE tenant_id = ? AND created_at >= ?",
                    (tid, cutoff),
                ).fetchone()[0]
            )
            positive = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM feedback_events
                    WHERE tenant_id = ? AND created_at >= ? AND rating = 1
                    """,
                    (tid, cutoff),
                ).fetchone()[0]
            )
            negative = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM feedback_events
                    WHERE tenant_id = ? AND created_at >= ? AND rating = 0
                    """,
                    (tid, cutoff),
                ).fetchone()[0]
            )
            pending = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM feedback_events
                    WHERE tenant_id = ? AND created_at >= ? AND status = 'pending'
                    """,
                    (tid, cutoff),
                ).fetchone()[0]
            )

            by_issue: list[dict[str, Any]] = []
            for row in conn.execute(
                """
                SELECT COALESCE(issue_type, 'unknown') AS issue_type, COUNT(*) AS c
                FROM feedback_events
                WHERE tenant_id = ? AND created_at >= ? AND rating = 0
                GROUP BY issue_type
                ORDER BY c DESC
                LIMIT 10
                """,
                (tid, cutoff),
            ).fetchall():
                by_issue.append({"issue_type": str(row["issue_type"]), "count": int(row["c"])})

            by_status: list[dict[str, Any]] = []
            for row in conn.execute(
                """
                SELECT COALESCE(status, 'pending') AS status, COUNT(*) AS c
                FROM feedback_events
                WHERE tenant_id = ? AND created_at >= ?
                GROUP BY status
                ORDER BY c DESC
                """,
                (tid, cutoff),
            ).fetchall():
                by_status.append({"status": str(row["status"]), "count": int(row["c"])})

            return {
                "since_days": days,
                "tenant_id": tid,
                "total": total,
                "positive": positive,
                "negative": negative,
                "pending_triage": pending,
                "by_issue_type": by_issue,
                "by_status": by_status,
            }
        finally:
            conn.close()
