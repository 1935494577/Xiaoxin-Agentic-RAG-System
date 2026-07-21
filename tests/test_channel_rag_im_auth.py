"""IM internal auth + ensure_chat_session for channel RAG bridge."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from starlette.requests import Request

ROOT_SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))


def test_ensure_chat_session_uses_fixed_id(tmp_path, monkeypatch):
    from api import chat_session_store as store

    db = tmp_path / "chat.db"
    monkeypatch.setattr(store.settings, "chat_sessions_db_path", db)
    store.init_chat_session_db()
    row = store.ensure_chat_session("im-wecom-abc", "user-1", title="IM")
    assert row["id"] == "im-wecom-abc"
    assert store.get_session("im-wecom-abc", "user-1") is not None


def test_im_internal_auth_loopback():
    from auth.im_internal import resolve_im_internal_user

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat/stream",
        "headers": [
            (b"x-im-internal", b"1"),
            (b"x-im-user-id", b"im-user-1"),
            (b"x-im-user-department", b"general"),
        ],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)
    user = resolve_im_internal_user(request)
    assert user is not None
    assert user["id"] == "im-user-1"
