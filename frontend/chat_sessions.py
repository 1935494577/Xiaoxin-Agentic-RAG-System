"""Frontend helpers for persisted chat sessions (SQLite via API)."""

from __future__ import annotations

from typing import Any

import httpx

import streamlit_common as scom


def list_sessions(api_base: str, user_id: str) -> list[dict[str, Any]]:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.get("/chat/sessions", params={"user_id": user_id})
        if r.status_code == 200:
            return r.json()
    except (httpx.TimeoutException, httpx.ConnectError):
        pass
    return []


def create_session(api_base: str, user_id: str, *, title: str = "新对话") -> dict[str, Any] | None:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.post("/chat/sessions", json={"user_id": user_id, "title": title})
        if r.status_code == 200:
            return r.json()
    except (httpx.TimeoutException, httpx.ConnectError):
        pass
    return None


def load_messages(api_base: str, user_id: str, session_id: str) -> list[dict[str, Any]]:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.get(
                f"/chat/sessions/{session_id}/messages",
                params={"user_id": user_id},
            )
        if r.status_code == 200:
            return r.json()
    except (httpx.TimeoutException, httpx.ConnectError):
        pass
    return []


def append_messages(
    api_base: str,
    user_id: str,
    session_id: str,
    messages: list[dict[str, Any]],
    *,
    auto_title_from: str | None = None,
) -> bool:
    payload: dict[str, Any] = {
        "user_id": user_id,
        "messages": messages,
    }
    if auto_title_from:
        payload["auto_title_from"] = auto_title_from
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.post(f"/chat/sessions/{session_id}/messages", json=payload)
        return r.status_code == 200
    except (httpx.TimeoutException, httpx.ConnectError):
        return False


def delete_session(api_base: str, user_id: str, session_id: str) -> bool:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.delete(f"/chat/sessions/{session_id}", params={"user_id": user_id})
        return r.status_code == 200
    except (httpx.TimeoutException, httpx.ConnectError):
        return False
