"""SQLite-backed chat sessions keyed by user_id."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from config import settings

_lock = Lock()
_msg_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_MSG_CACHE_TTL = 30.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> Path:
    return settings.chat_sessions_db_path


def init_chat_session_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '新对话',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    meta_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                    ON chat_sessions(user_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON chat_messages(session_id, id);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _invalidate_cache(session_id: str) -> None:
    _msg_cache.pop(session_id, None)


def list_sessions(user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    uid = user_id.strip()
    if not uid:
        return []
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM chat_sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (uid, max(1, min(limit, 200))),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def create_session(user_id: str, *, title: str = "新对话") -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    sid = uuid.uuid4().hex
    now = _utc_now()
    row = {
        "id": sid,
        "user_id": uid,
        "title": (title or "新对话").strip()[:128] or "新对话",
        "created_at": now,
        "updated_at": now,
    }
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row["id"], row["user_id"], row["title"], row["created_at"], row["updated_at"]),
            )
            conn.commit()
        finally:
            conn.close()
    return row


def get_session(session_id: str, user_id: str) -> dict[str, Any] | None:
    sid = session_id.strip()
    uid = user_id.strip()
    if not sid or not uid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
                (sid, uid),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def update_session_title(session_id: str, user_id: str, title: str) -> dict[str, Any] | None:
    sess = get_session(session_id, user_id)
    if not sess:
        return None
    new_title = (title or "").strip()[:128] or sess["title"]
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (new_title, now, session_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()
    sess["title"] = new_title
    sess["updated_at"] = now
    return sess


def delete_session(session_id: str, user_id: str) -> bool:
    sid = session_id.strip()
    uid = user_id.strip()
    if not sid or not uid:
        return False
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
                (sid, uid),
            )
            conn.commit()
            deleted = cur.rowcount > 0
        finally:
            conn.close()
    if deleted:
        _invalidate_cache(sid)
    return deleted


def list_messages(session_id: str, user_id: str) -> list[dict[str, Any]]:
    if not get_session(session_id, user_id):
        return []

    now = time.monotonic()
    cached = _msg_cache.get(session_id)
    if cached and now - cached[0] <= _MSG_CACHE_TTL:
        return list(cached[1])

    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT role, content, meta_json, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                meta = None
                if r["meta_json"]:
                    try:
                        meta = json.loads(r["meta_json"])
                    except json.JSONDecodeError:
                        meta = None
                item: dict[str, Any] = {"role": r["role"], "content": r["content"]}
                if meta:
                    item["meta"] = meta
                out.append(item)
        finally:
            conn.close()

    _msg_cache[session_id] = (now, out)
    return out


def append_messages(
    session_id: str,
    user_id: str,
    messages: list[dict[str, Any]],
    *,
    auto_title_from: str | None = None,
) -> list[dict[str, Any]]:
    sess = get_session(session_id, user_id)
    if not sess:
        raise ValueError("session not found")

    if not messages:
        return list_messages(session_id, user_id)

    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            for msg in messages:
                role = str(msg.get("role") or "").strip()
                content = str(msg.get("content") or "")
                if role not in {"user", "assistant"}:
                    continue
                meta = msg.get("meta")
                meta_json = json.dumps(meta, ensure_ascii=False) if meta else None
                conn.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content, meta_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, role, content, meta_json, now),
                )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            if auto_title_from and sess.get("title") == "新对话":
                title = auto_title_from.strip()[:40] or "新对话"
                conn.execute(
                    "UPDATE chat_sessions SET title = ? WHERE id = ?",
                    (title, session_id),
                )
            conn.commit()
        finally:
            conn.close()

    _invalidate_cache(session_id)
    return list_messages(session_id, user_id)
