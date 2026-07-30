"""Chitchat short-circuit: skip retrieval for greetings / courtesy."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.chitchat import canned_chitchat_reply, is_chitchat_message  # noqa: E402


def test_exact_greetings_are_chitchat():
    for q in ("你好", "您好", "谢谢", "多谢", "再见", "拜拜", "hi", "hello"):
        assert is_chitchat_message(q), q


def test_kb_questions_are_not_chitchat():
    for q in ("请假制度是什么", "今日萧山区天气", "扫描速记有哪些注意事项", "你好，公司年假怎么算"):
        assert not is_chitchat_message(q), q


def test_canned_reply_non_empty():
    text = canned_chitchat_reply("你好")
    assert "你好" in text or "您好" in text
    assert len(text) < 80


def test_detect_query_intent_chitchat():
    from retrieval.query_understanding import detect_query_intent

    assert detect_query_intent("你好") == "chitchat"
    assert detect_query_intent("请假流程") == "kb"
