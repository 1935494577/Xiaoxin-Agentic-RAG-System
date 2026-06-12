"""SQLite-backed user feedback events (same DB as chat sessions)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from config import settings

_lock = Lock()
DEFAULT_TENANT = "internal"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> Path:
    return settings.chat_sessions_db_path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


_TRIAGE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("status", "TEXT NOT NULL DEFAULT 'pending'"),
    ("issue_type", "TEXT"),
    ("severity", "TEXT"),
    ("human_review_required", "INTEGER"),
    ("triage_json", "TEXT"),
    ("triage_summary", "TEXT"),
    ("triage_error", "TEXT"),
    ("updated_at", "TEXT"),
)


def _migrate_feedback_columns(conn: sqlite3.Connection) -> None:
    existing = {str(r[1]) for r in conn.execute("PRAGMA table_info(feedback_events)")}
    for name, ddl in _TRIAGE_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE feedback_events ADD COLUMN {name} {ddl}")


def init_feedback_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS feedback_events (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'internal',
                    user_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    trace_id TEXT,
                    session_id TEXT,
                    message_id TEXT,
                    question TEXT,
                    answer_preview TEXT,
                    answer_mode TEXT,
                    correction TEXT,
                    context_count INTEGER,
                    sources_json TEXT,
                    trace_snapshot_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_feedback_user_created
                    ON feedback_events(user_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_feedback_trace
                    ON feedback_events(trace_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_rating_created
                    ON feedback_events(rating, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_feedback_created
                    ON feedback_events(created_at DESC);
                """
            )
            _migrate_feedback_columns(conn)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_feedback_status_created "
                "ON feedback_events(status, created_at DESC)"
            )
            conn.commit()
        finally:
            conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    sources: list[str] = []
    if d.get("sources_json"):
        try:
            raw = json.loads(d["sources_json"])
            if isinstance(raw, list):
                sources = [str(x) for x in raw if str(x).strip()]
        except json.JSONDecodeError:
            sources = []
    d["sources"] = sources
    d.pop("sources_json", None)

    trace_snapshot = None
    if d.get("trace_snapshot_json"):
        try:
            trace_snapshot = json.loads(d["trace_snapshot_json"])
        except json.JSONDecodeError:
            trace_snapshot = None
    d["trace_snapshot"] = trace_snapshot
    d.pop("trace_snapshot_json", None)

    triage_raw = None
    if d.get("triage_json"):
        try:
            triage_raw = json.loads(d["triage_json"])
        except json.JSONDecodeError:
            triage_raw = None
    d["suggested_actions"] = (
        list(triage_raw.get("suggested_actions") or []) if isinstance(triage_raw, dict) else []
    )
    d.pop("triage_json", None)

    if d.get("human_review_required") is not None:
        d["human_review_required"] = bool(d["human_review_required"])

    d.setdefault("status", "pending")
    return d


def insert_feedback(
    *,
    user_id: str,
    rating: int,
    tenant_id: str = DEFAULT_TENANT,
    trace_id: str | None = None,
    session_id: str | None = None,
    message_id: str | None = None,
    question: str | None = None,
    answer_preview: str | None = None,
    answer_mode: str | None = None,
    correction: str | None = None,
) -> str:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    fid = uuid.uuid4().hex
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO feedback_events (
                    id, tenant_id, user_id, rating, trace_id, session_id, message_id,
                    question, answer_preview, answer_mode, correction, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT,
                    uid,
                    int(rating),
                    (trace_id or "").strip() or None,
                    (session_id or "").strip() or None,
                    (message_id or "").strip() or None,
                    (question or "").strip() or None,
                    (answer_preview or "").strip()[:4000] or None,
                    (answer_mode or "").strip() or None,
                    (correction or "").strip() or None,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return fid


def enrich_feedback(
    feedback_id: str,
    *,
    context_count: int | None = None,
    sources: list[str] | None = None,
    trace_snapshot: dict[str, Any] | None = None,
    question: str | None = None,
    answer_mode: str | None = None,
) -> bool:
    fid = feedback_id.strip()
    if not fid:
        return False
    sources_json = json.dumps(sources or [], ensure_ascii=False) if sources is not None else None
    trace_json = (
        json.dumps(trace_snapshot, ensure_ascii=False) if trace_snapshot is not None else None
    )
    with _lock:
        conn = _connect()
        try:
            sets: list[str] = []
            params: list[Any] = []
            if context_count is not None:
                sets.append("context_count = ?")
                params.append(int(context_count))
            if sources_json is not None:
                sets.append("sources_json = ?")
                params.append(sources_json)
            if trace_json is not None:
                sets.append("trace_snapshot_json = ?")
                params.append(trace_json)
            if question:
                sets.append("question = COALESCE(question, ?)")
                params.append(question.strip()[:8000])
            if answer_mode:
                sets.append("answer_mode = COALESCE(answer_mode, ?)")
                params.append(answer_mode.strip()[:64])
            if not sets:
                return False
            params.append(fid)
            cur = conn.execute(
                f"UPDATE feedback_events SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def get_feedback(feedback_id: str) -> dict[str, Any] | None:
    fid = feedback_id.strip()
    if not fid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM feedback_events WHERE id = ?",
                (fid,),
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()


def set_feedback_status(feedback_id: str, status: str) -> bool:
    fid = feedback_id.strip()
    if not fid:
        return False
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "UPDATE feedback_events SET status = ?, updated_at = ? WHERE id = ?",
                (status.strip(), now, fid),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def save_triage_result(
    feedback_id: str,
    *,
    issue_type: str,
    severity: str,
    human_review_required: bool,
    summary: str,
    suggested_actions: list[dict[str, Any]] | None = None,
    triage_mode: str = "rule",
    triage_error: str | None = None,
) -> dict[str, Any] | None:
    fid = feedback_id.strip()
    if not fid:
        return None
    now = _utc_now()
    triage_payload = {
        "issue_type": issue_type,
        "severity": severity,
        "human_review_required": human_review_required,
        "summary": summary,
        "suggested_actions": suggested_actions or [],
        "mode": triage_mode,
    }
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "SELECT status FROM feedback_events WHERE id = ?",
                (fid,),
            ).fetchone()
            if not cur:
                return None
            current = str(cur["status"] or "pending")
            if current != "pending":
                row = conn.execute("SELECT * FROM feedback_events WHERE id = ?", (fid,)).fetchone()
                return _row_to_dict(row) if row else None
            conn.execute(
                """
                UPDATE feedback_events SET
                    status = 'triaged',
                    issue_type = ?,
                    severity = ?,
                    human_review_required = ?,
                    triage_json = ?,
                    triage_summary = ?,
                    triage_error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    issue_type,
                    severity,
                    1 if human_review_required else 0,
                    json.dumps(triage_payload, ensure_ascii=False),
                    summary[:500] if summary else None,
                    triage_error,
                    now,
                    fid,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM feedback_events WHERE id = ?", (fid,)).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()


def list_feedback(
    *,
    user_id: str | None = None,
    trace_id: str | None = None,
    rating: int | None = None,
    status: str | None = None,
    sort: str = "created_desc",
    tenant_id: str = DEFAULT_TENANT,
    since_days: int | None = 7,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    lim = max(1, min(int(limit), 50))
    off = max(0, int(offset))
    clauses = ["tenant_id = ?"]
    params: list[Any] = [(tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT]

    if user_id and user_id.strip():
        clauses.append("user_id = ?")
        params.append(user_id.strip())
    if trace_id and trace_id.strip():
        clauses.append("trace_id = ?")
        params.append(trace_id.strip())
    if rating is not None:
        clauses.append("rating = ?")
        params.append(int(rating))
    if status and status.strip():
        clauses.append("status = ?")
        params.append(status.strip())
    if since_days is not None and since_days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=int(since_days))).isoformat()
        clauses.append("created_at >= ?")
        params.append(cutoff)

    where = " AND ".join(clauses)
    order = "created_at DESC"
    if sort == "severity_desc":
        order = (
            "CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 ELSE 3 END, "
            "created_at DESC"
        )
    elif sort == "severity_asc":
        order = (
            "CASE severity WHEN 'low' THEN 0 WHEN 'medium' THEN 1 WHEN 'high' THEN 2 ELSE 3 END, "
            "created_at DESC"
        )
    with _lock:
        conn = _connect()
        try:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS c FROM feedback_events WHERE {where}",
                params,
            ).fetchone()
            total = int(total_row["c"]) if total_row else 0
            rows = conn.execute(
                f"""
                SELECT * FROM feedback_events
                WHERE {where}
                ORDER BY {order}
                LIMIT ? OFFSET ?
                """,
                [*params, lim, off],
            ).fetchall()
            return [_row_to_dict(r) for r in rows], total
        finally:
            conn.close()


def append_feedback_jsonl(row: dict[str, Any]) -> None:
    """Append one feedback record to JSONL export file."""
    path = settings.data_feedback_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
