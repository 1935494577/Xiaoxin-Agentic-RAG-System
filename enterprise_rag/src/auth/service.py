"""Bootstrap default accounts and auth service."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from auth.password import verify_password
from auth.store import (
    count_users,
    create_session,
    create_user,
    delete_session,
    get_session_user,
    get_user_by_username,
    init_auth_db,
    list_users,
    purge_expired_sessions,
    set_user_active,
    update_password,
)
from config import settings
from security.access_control import DEPARTMENTS
from security.department_features import FULL_ACCESS_DEPARTMENT

STATE_KEY = "auth_user"

BOOTSTRAP_ACCOUNTS: list[tuple[str, str]] = [
    ("tech1", FULL_ACCESS_DEPARTMENT),
    ("tech2", FULL_ACCESS_DEPARTMENT),
    ("tech3", FULL_ACCESS_DEPARTMENT),
    ("ops1", "运营部"),
    ("media1", "媒体部"),
    ("edit1", "剪辑部"),
]


def _bootstrap_path() -> Path:
    return Path(settings.auth_bootstrap_credentials_path)


def seed_default_users_if_empty() -> list[dict[str, str]] | None:
    init_auth_db()
    purge_expired_sessions()
    if count_users() > 0:
        return None
    created: list[dict[str, str]] = []
    for username, department in BOOTSTRAP_ACCOUNTS:
        password = secrets.token_urlsafe(10)
        create_user(username=username, password=password, department=department, display_name=username)
        created.append(
            {
                "username": username,
                "password": password,
                "department": department,
            }
        )
    _write_bootstrap_file(created)
    return created


def _write_bootstrap_file(rows: list[dict[str, str]]) -> None:
    path = _bootstrap_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 初始账号（仅首次启动生成，请妥善保管并尽快修改密码）",
        "# 技术部 3 个账号拥有全部管理功能；其他部门各 1 个。",
        "",
    ]
    for row in rows:
        lines.append(f"{row['department']}\t{row['username']}\t{row['password']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def login(username: str, password: str, *, remember: bool = True) -> dict[str, Any]:
    user = get_user_by_username(username)
    if not user or not int(user.get("is_active", 0)):
        raise ValueError("invalid_credentials")
    if not verify_password(password, str(user["password_hash"]), str(user["password_salt"])):
        raise ValueError("invalid_credentials")
    token = secrets.token_urlsafe(32)
    ttl = (
        int(settings.auth_session_remember_ttl_hours)
        if remember
        else int(settings.auth_session_ttl_hours)
    )
    create_session(user_id=str(user["id"]), token=token, ttl_hours=ttl)
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "tenant_id": user.get("tenant_id") or "internal",
            "department": user["department"],
            "display_name": user.get("display_name") or user["username"],
        },
    }


def logout(token: str) -> None:
    if token:
        delete_session(token)


def resolve_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    return get_session_user(token)


def change_password(user_id: str, current_password: str, new_password: str) -> None:
    row = _get_user_with_secrets(user_id)
    if not row:
        raise ValueError("user_not_found")
    if not verify_password(current_password, str(row["password_hash"]), str(row["password_salt"])):
        raise ValueError("invalid_credentials")
    if len(new_password or "") < 6:
        raise ValueError("password_too_short")
    if not update_password(user_id, new_password):
        raise ValueError("update_failed")


def _get_user_with_secrets(user_id: str) -> dict[str, Any] | None:
    from auth.store import _connect, _lock

    uid = (user_id or "").strip()
    if not uid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, username, password_hash, password_salt, department FROM auth_users WHERE id = ?",
                (uid,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def admin_create_user(
    *,
    username: str,
    password: str,
    department: str,
    display_name: str = "",
) -> dict[str, Any]:
    dept = department.strip()
    if dept not in DEPARTMENTS:
        raise ValueError("invalid_department")
    if len(password or "") < 6:
        raise ValueError("password_too_short")
    return create_user(
        username=username,
        password=password,
        department=dept,
        display_name=display_name or username,
    )


def admin_reset_password(user_id: str, new_password: str) -> None:
    if len(new_password or "") < 6:
        raise ValueError("password_too_short")
    if not update_password(user_id, new_password):
        raise ValueError("user_not_found")


def admin_list_users_public() -> list[dict[str, Any]]:
    return [
        {
            "id": u["id"],
            "username": u["username"],
            "tenant_id": u.get("tenant_id") or "internal",
            "department": u["department"],
            "display_name": u.get("display_name") or u["username"],
            "is_active": bool(int(u.get("is_active") or 0)),
        }
        for u in list_users()
    ]
