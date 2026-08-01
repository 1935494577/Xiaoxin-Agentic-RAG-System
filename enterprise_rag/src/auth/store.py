"""SQLite user accounts and sessions."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from auth.password import hash_password, hash_session_token
from config import settings
from security.access_control import DEPARTMENTS, normalize_department

_lock = Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _db_path():
    return settings.auth_db_path


def init_auth_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'internal',
                    department TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_auth_users_dept ON auth_users(department);
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES auth_users(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
                """
            )
            conn.commit()
            try:
                conn.execute(
                    "ALTER TABLE auth_users ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'internal'"
                )
                conn.commit()
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def count_users() -> int:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM auth_users").fetchone()
            return int(row["c"]) if row else 0
        finally:
            conn.close()


def get_user_by_username(username: str) -> dict[str, Any] | None:
    name = (username or "").strip()
    if not name:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, username, password_hash, password_salt, tenant_id, department, display_name, "
                "is_active, created_at, updated_at FROM auth_users WHERE username = ? COLLATE NOCASE",
                (name,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    uid = (user_id or "").strip()
    if not uid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, username, tenant_id, department, display_name, is_active, created_at, updated_at "
                "FROM auth_users WHERE id = ?",
                (uid,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def list_users(*, department: str | None = None) -> list[dict[str, Any]]:
    with _lock:
        conn = _connect()
        try:
            if department:
                dept = normalize_department(department)
                rows = conn.execute(
                    "SELECT id, username, tenant_id, department, display_name, is_active, created_at, updated_at "
                    "FROM auth_users WHERE department = ? ORDER BY username",
                    (dept,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, username, tenant_id, department, display_name, is_active, created_at, updated_at "
                    "FROM auth_users ORDER BY department, username"
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def create_user(
    *,
    username: str,
    password: str,
    department: str,
    display_name: str = "",
    tenant_id: str = "internal",
) -> dict[str, Any]:
    name = (username or "").strip()
    if not name:
        raise ValueError("username required")
    dept = normalize_department(department)
    if dept not in DEPARTMENTS:
        raise ValueError(f"invalid department: {department}")
    tenant = (tenant_id or "").strip()[:64] or "internal"
    pwd_hash, pwd_salt = hash_password(password)
    now = _iso(_utc_now())
    row = {
        "id": str(uuid.uuid4()),
        "username": name,
        "password_hash": pwd_hash,
        "password_salt": pwd_salt,
        "tenant_id": tenant,
        "department": dept,
        "display_name": (display_name or name).strip(),
        "is_active": 1,
        "created_at": now,
        "updated_at": now,
    }
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO auth_users (id, username, password_hash, password_salt, tenant_id, department, "
                "display_name, is_active, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    row["id"],
                    row["username"],
                    row["password_hash"],
                    row["password_salt"],
                    row["tenant_id"],
                    row["department"],
                    row["display_name"],
                    row["is_active"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("username already exists") from exc
        finally:
            conn.close()
    return get_user_by_id(row["id"]) or row


def update_password(user_id: str, new_password: str) -> bool:
    uid = (user_id or "").strip()
    if not uid or not new_password:
        return False
    pwd_hash, pwd_salt = hash_password(new_password)
    now = _iso(_utc_now())
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "UPDATE auth_users SET password_hash = ?, password_salt = ?, updated_at = ? WHERE id = ?",
                (pwd_hash, pwd_salt, now, uid),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def set_user_active(user_id: str, *, active: bool) -> bool:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "UPDATE auth_users SET is_active = ?, updated_at = ? WHERE id = ?",
                (1 if active else 0, _iso(_utc_now()), user_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def update_user_display_name(user_id: str, display_name: str) -> bool:
    uid = (user_id or "").strip()
    name = (display_name or "").strip()[:64]
    if not uid:
        return False
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "UPDATE auth_users SET display_name = ?, updated_at = ? WHERE id = ?",
                (name, _iso(_utc_now()), uid),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def create_session(*, user_id: str, token: str, ttl_hours: int) -> None:
    expires = _utc_now() + timedelta(hours=max(1, ttl_hours))
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO auth_sessions (token_hash, user_id, expires_at, created_at) VALUES (?,?,?,?)",
                (hash_session_token(token), user_id, _iso(expires), _iso(_utc_now())),
            )
            conn.commit()
        finally:
            conn.close()


def delete_session(token: str) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (hash_session_token(token),))
            conn.commit()
        finally:
            conn.close()


def get_session_user(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    th = hash_session_token(token)
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                """
                SELECT u.id, u.username, u.tenant_id, u.department, u.display_name, u.is_active, s.expires_at
                FROM auth_sessions s
                JOIN auth_users u ON u.id = s.user_id
                WHERE s.token_hash = ?
                """,
                (th,),
            ).fetchone()
            if not row:
                return None
            if not int(row["is_active"]):
                return None
            expires = datetime.fromisoformat(str(row["expires_at"]))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires <= _utc_now():
                conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (th,))
                conn.commit()
                return None
            return {
                "id": row["id"],
                "username": row["username"],
                "tenant_id": row["tenant_id"],
                "department": row["department"],
                "display_name": row["display_name"],
            }
        finally:
            conn.close()


def purge_expired_sessions() -> int:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (_iso(_utc_now()),))
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()
