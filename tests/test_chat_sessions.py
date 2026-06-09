"""Chat session SQLite store tests."""

import pytest

from api.chat_session_store import (
    append_messages,
    create_session,
    delete_session,
    init_chat_session_db,
    list_messages,
    list_sessions,
)
from config import settings


@pytest.fixture()
def session_db(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    init_chat_session_db()
    return db


def test_create_and_list_sessions(session_db):
    s1 = create_session("user_a", title="对话一")
    s2 = create_session("user_a", title="对话二")
    create_session("user_b")

    rows = list_sessions("user_a")
    assert len(rows) == 2
    assert {r["id"] for r in rows} == {s1["id"], s2["id"]}


def test_append_and_load_messages(session_db):
    sess = create_session("u1")
    append_messages(
        sess["id"],
        "u1",
        [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好", "meta": {"sources": []}},
        ],
        auto_title_from="你好",
    )
    msgs = list_messages(sess["id"], "u1")
    assert len(msgs) == 2
    assert msgs[0]["content"] == "你好"
    assert msgs[1]["meta"] == {"sources": []}

    sessions = list_sessions("u1")
    assert sessions[0]["title"] == "你好"


def test_delete_session(session_db):
    sess = create_session("u1")
    append_messages(sess["id"], "u1", [{"role": "user", "content": "x"}])
    assert delete_session(sess["id"], "u1")
    assert list_sessions("u1") == []
