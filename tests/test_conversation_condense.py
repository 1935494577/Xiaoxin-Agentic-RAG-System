"""Step 1: condense + topic_shift tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.conversation.query_condense import (  # noqa: E402
    condense_turn,
    needs_condense,
    parse_condense_response,
)


def test_needs_condense_false_without_history():
    assert needs_condense("什么是 RAG？", []) is False


def test_needs_condense_true_for_pronoun_followup():
    hist = [{"role": "user", "content": "超脑阅读要求是什么？"}, {"role": "assistant", "content": "…"}]
    assert needs_condense("它呢？", hist) is True


def test_needs_condense_false_for_long_standalone():
    hist = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    msg = "请介绍一下企业知识库混合检索的向量权重与 BM25 权重分别是如何配置的？"
    assert needs_condense(msg, hist) is False


def test_parse_condense_response_json():
    raw = '{"standalone_query": "3年级超脑阅读要求", "topic_shift": false}'
    q, shift = parse_condense_response(raw)
    assert q == "3年级超脑阅读要求"
    assert shift is False


def test_parse_condense_response_fallback_lines():
    raw = "topic_shift: true\nstandalone_query: 今天天气怎么样"
    q, shift = parse_condense_response(raw)
    assert shift is True
    assert "天气" in q


def test_condense_turn_no_history():
    out = condense_turn("hello", [], llm_runtime={})
    assert out.standalone_query == "hello"
    assert out.topic_shift is False
    assert out.used_llm is False


def test_condense_turn_shortcut_standalone():
    hist = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    msg = "请详细说明混合检索中向量检索与 BM25 检索的融合公式及默认权重配置。"
    out = condense_turn(msg, hist, llm_runtime={"llm_api_key": "k"})
    assert out.standalone_query == msg
    assert out.used_llm is False


@patch("agent.conversation.query_condense.OpenAI")
def test_condense_turn_llm_followup(mock_openai):
    client = MagicMock()
    mock_openai.return_value = client
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content='{"standalone_query":"3年级超脑阅读要求","topic_shift":false}'))]
    client.chat.completions.create.return_value = resp

    hist = [
        {"role": "user", "content": "1-3年级超脑阅读要求是什么？"},
        {"role": "assistant", "content": "要求包括…"},
    ]
    out = condense_turn(
        "那三年级呢？",
        hist,
        llm_runtime={"llm_api_key": "test-key", "chat_model": "gpt-4o-mini"},
    )
    assert out.used_llm is True
    assert "三年级" in out.standalone_query or "3" in out.standalone_query
    assert out.topic_shift is False
