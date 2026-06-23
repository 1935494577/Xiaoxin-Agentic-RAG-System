"""SQLite-backed user profile (display name, avatar, department)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from config import settings
from security.access_control import DEPARTMENTS, normalize_department

_lock = Lock()
_DEFAULT_DEPT = "技术部"
_MAX_AVATAR_LEN = 600_000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path():
    return settings.chat_sessions_db_path


def init_user_profile_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL DEFAULT '',
                    avatar_url TEXT NOT NULL DEFAULT '',
                    department TEXT NOT NULL DEFAULT '技术部',
                    ai_display_name TEXT NOT NULL DEFAULT '',
                    ai_avatar_url TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                """
            )
            for ddl in (
                "ALTER TABLE user_profiles ADD COLUMN ai_display_name TEXT NOT NULL DEFAULT ''",
                "ALTER TABLE user_profiles ADD COLUMN ai_avatar_url TEXT NOT NULL DEFAULT ''",
            ):
                try:
                    conn.execute(ddl)
                except sqlite3.OperationalError:
                    pass
            conn.commit()
        finally:
            conn.close()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _default_row(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "display_name": "",
        "avatar_url": "",
        "department": _DEFAULT_DEPT,
        "ai_display_name": "",
        "ai_avatar_url": "",
        "updated_at": _utc_now(),
    }


def _validate_department(department: str) -> str:
    dept = normalize_department(department)
    if dept not in DEPARTMENTS:
        raise ValueError(f"invalid department: {department}")
    return dept


def _validate_avatar(avatar_url: str) -> str:
    url = (avatar_url or "").strip()
    if not url:
        return ""
    if len(url) > _MAX_AVATAR_LEN:
        raise ValueError("avatar too large")
    if not url.startswith("data:image/"):
        raise ValueError("avatar must be a data:image URL")
    return url


def get_profile(user_id: str) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT user_id, display_name, avatar_url, department, "
                "ai_display_name, ai_avatar_url, updated_at "
                "FROM user_profiles WHERE user_id = ?",
                (uid,),
            ).fetchone()
            if row:
                return dict(row)
            default = _default_row(uid)
            conn.execute(
                "INSERT INTO user_profiles (user_id, display_name, avatar_url, department, "
                "ai_display_name, ai_avatar_url, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    uid,
                    default["display_name"],
                    default["avatar_url"],
                    default["department"],
                    default["ai_display_name"],
                    default["ai_avatar_url"],
                    default["updated_at"],
                ),
            )
            conn.commit()
            return default
        finally:
            conn.close()


def upsert_profile(
    user_id: str,
    *,
    display_name: str | None = None,
    avatar_url: str | None = None,
    department: str | None = None,
    ai_display_name: str | None = None,
    ai_avatar_url: str | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    current = get_profile(uid)
    name = current["display_name"] if display_name is None else display_name.strip()[:64]
    avatar = current["avatar_url"] if avatar_url is None else _validate_avatar(avatar_url)
    dept = current["department"] if department is None else _validate_department(department)
    ai_name = (
        current["ai_display_name"]
        if ai_display_name is None
        else ai_display_name.strip()[:64]
    )
    ai_avatar = (
        current["ai_avatar_url"] if ai_avatar_url is None else _validate_avatar(ai_avatar_url)
    )
    updated = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO user_profiles (
                    user_id, display_name, avatar_url, department,
                    ai_display_name, ai_avatar_url, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    avatar_url = excluded.avatar_url,
                    department = excluded.department,
                    ai_display_name = excluded.ai_display_name,
                    ai_avatar_url = excluded.ai_avatar_url,
                    updated_at = excluded.updated_at
                """,
                (uid, name, avatar, dept, ai_name, ai_avatar, updated),
            )
            conn.commit()
            row = conn.execute(
                "SELECT user_id, display_name, avatar_url, department, "
                "ai_display_name, ai_avatar_url, updated_at "
                "FROM user_profiles WHERE user_id = ?",
                (uid,),
            ).fetchone()
            return dict(row) if row else current
        finally:
            conn.close()


def _fetch_profile_row(conn: sqlite3.Connection, user_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT user_id, display_name, avatar_url, department, "
        "ai_display_name, ai_avatar_url, updated_at "
        "FROM user_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def _profile_has_legacy_assets(row: dict[str, Any]) -> bool:
    return bool(
        (row.get("display_name") or "").strip()
        or (row.get("avatar_url") or "").strip()
        or (row.get("ai_display_name") or "").strip()
        or (row.get("ai_avatar_url") or "").strip()
    )


def _looks_like_login_placeholder(name: str, user_id: str) -> bool:
    n = (name or "").strip()
    if not n:
        return True
    if n == user_id:
        return True
    return n.isascii() and n.isalnum() and len(n) <= 32


def merge_legacy_user(legacy_user_id: str, target_user_id: str) -> dict[str, Any]:
    """Move avatar/nickname and chat sessions from pre-auth anonymous user id to auth account."""
    legacy = legacy_user_id.strip()
    target = target_user_id.strip()
    if not legacy or not target:
        raise ValueError("user_id required")
    if legacy == target:
        return get_profile(target)

    with _lock:
        conn = _connect()
        try:
            legacy_row = _fetch_profile_row(conn, legacy)
            if not legacy_row or not _profile_has_legacy_assets(legacy_row):
                return get_profile(target)

            target_row = _fetch_profile_row(conn, target)
            if target_row is None:
                target_row = _default_row(target)

            merged_name = (target_row.get("display_name") or "").strip()
            legacy_name = (legacy_row.get("display_name") or "").strip()[:64]
            if legacy_name and _looks_like_login_placeholder(merged_name, target):
                merged_name = legacy_name

            merged_avatar = (target_row.get("avatar_url") or "").strip() or legacy_row.get("avatar_url") or ""
            merged_ai_name = (target_row.get("ai_display_name") or "").strip() or (
                legacy_row.get("ai_display_name") or ""
            ).strip()[:64]
            merged_ai_avatar = (target_row.get("ai_avatar_url") or "").strip() or (
                legacy_row.get("ai_avatar_url") or ""
            )

            dept = target_row.get("department") or legacy_row.get("department") or _DEFAULT_DEPT
            updated = _utc_now()
            conn.execute(
                """
                INSERT INTO user_profiles (
                    user_id, display_name, avatar_url, department,
                    ai_display_name, ai_avatar_url, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    avatar_url = excluded.avatar_url,
                    department = excluded.department,
                    ai_display_name = excluded.ai_display_name,
                    ai_avatar_url = excluded.ai_avatar_url,
                    updated_at = excluded.updated_at
                """,
                (
                    target,
                    merged_name,
                    merged_avatar,
                    dept,
                    merged_ai_name,
                    merged_ai_avatar,
                    updated,
                ),
            )
            conn.execute(
                "UPDATE chat_sessions SET user_id = ? WHERE user_id = ?",
                (target, legacy),
            )
            conn.commit()
            row = _fetch_profile_row(conn, target)
            result = row if row else get_profile(target)
        finally:
            conn.close()

    if merged_name:
        try:
            from auth.store import update_user_display_name

            update_user_display_name(target, merged_name)
        except Exception:
            pass
    return result
