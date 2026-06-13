"""Rolling summary + session store tests."""

from unittest.mock import MagicMock, patch

import pytest

from agent.conversation.rolling_summary import (
    augment_system_with_summary,
    count_user_turns,
    format_messages_for_summary,
    should_update_summary,
    summarize_conversation,
)
from api.chat_session_store import (
    clear_rolling_summary,
    get_rolling_summary,
    init_chat_session_db,
    set_rolling_summary,
)
from config import settings


@pytest.fixture()
def session_db(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    init_chat_session_db()
    return db


def test_should_update_summary_thresholds():
    assert should_update_summary(turn_count=1, history_chars=5000) is False
    assert should_update_summary(turn_count=6, history_chars=1000) is False
    assert should_update_summary(turn_count=6, history_chars=4000) is True


def test_augment_system_with_summary():
    out = augment_system_with_summary("你是助手。", "用户讨论了阅读训练。")
    assert "此前对话摘要" in out
    assert "阅读训练" in out


def test_augment_system_empty():
    assert augment_system_with_summary("base", "") == "base"


@patch("agent.conversation.rolling_summary.OpenAI")
def test_summarize_conversation(mock_openai):
    client = MagicMock()
    mock_openai.return_value = client
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content="用户咨询了超脑阅读与天气。"))]
    client.chat.completions.create.return_value = resp

    text = summarize_conversation(
        previous_summary="旧摘要",
        messages=[
            {"role": "user", "content": "超脑阅读？"},
            {"role": "assistant", "content": "要求…"},
        ],
        llm_runtime={"llm_api_key": "k"},
    )
    assert "阅读" in text or "天气" in text


def test_session_rolling_summary_roundtrip(session_db):
    from api.chat_session_store import append_messages, create_session

    sess = create_session("u1")
    set_rolling_summary(sess["id"], "u1", "摘要内容")
    assert get_rolling_summary(sess["id"], "u1") == "摘要内容"
    clear_rolling_summary(sess["id"], "u1")
    assert get_rolling_summary(sess["id"], "u1") == ""
    append_messages(sess["id"], "u1", [{"role": "user", "content": "hi"}])
    assert get_rolling_summary(sess["id"], "u1") == ""


def test_format_and_count():
    msgs = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]
    assert count_user_turns(msgs) == 2
    assert "用户" in format_messages_for_summary(msgs)
