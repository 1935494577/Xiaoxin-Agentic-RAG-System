"""Tool routing for realtime queries and noisy voice input."""

from __future__ import annotations

import pytest

from agent.tools.runtime.routing import (
    is_web_search_affirmative_followup,
    normalize_tool_routing_question,
    question_needs_realtime_tools,
    recent_assistant_offered_web_search,
    resolve_web_search_query,
    should_use_web_search_followup,
)


def test_normalize_voice_weather_query():
    noisy = "电脑。今日萧山区天气。我就。我就。"
    assert normalize_tool_routing_question(noisy) == "今日萧山区天气"


def test_realtime_tools_for_weather_even_with_noise():
    noisy = "电脑。今日萧山区天气。我就。我就。"
    assert question_needs_realtime_tools(noisy) is True


def test_realtime_tools_plain_weather():
    assert question_needs_realtime_tools("萧山区今天天气") is True


def test_realtime_tools_not_kb_training_question():
    assert question_needs_realtime_tools("超脑阅读训练建议") is False


def test_realtime_tools_for_ai_industry_trend():
    assert question_needs_realtime_tools("2025年AI发展") is True
    assert question_needs_realtime_tools("人工智能发展趋势") is True
    assert question_needs_realtime_tools("大模型行业动态") is True


def test_realtime_tools_for_recent_year_topic():
    assert question_needs_realtime_tools("今年科技热点") is True


def test_detect_query_intent_realtime_for_ai_trend():
    from retrieval.query_understanding import detect_query_intent

    assert detect_query_intent("2025年AI发展") == "realtime"


def test_web_search_affirmative_followup():
    assert is_web_search_affirmative_followup("需要") is True
    assert is_web_search_affirmative_followup("@RAG agent 需要") is True
    assert is_web_search_affirmative_followup("好的，查一下") is True
    assert is_web_search_affirmative_followup("长鑫存储今日财报") is False


def test_web_search_followup_after_assistant_offer():
    history = [
        {"role": "user", "content": "长鑫存储今日财报"},
        {
            "role": "assistant",
            "content": "长鑫存储是非上市公司…需要我查吗？我可以帮你上网搜索一下喵~",
        },
    ]
    assert recent_assistant_offered_web_search(history) is True
    assert should_use_web_search_followup("需要", history) is True
    query = resolve_web_search_query("需要", history)
    assert "长鑫存储" in query


def test_web_search_followup_not_without_offer():
    history = [
        {"role": "user", "content": "组织架构"},
        {"role": "assistant", "content": "请补充你想了解哪个部门。"},
    ]
    assert should_use_web_search_followup("需要", history) is False


def test_realtime_tool_turn_for_kb_intent_with_today_keyword():
    from agent.stream_chat import _is_realtime_tool_turn

    state = {
        "question": "长鑫存储今日财报",
        "turn_meta": {"query_intent": "kb"},
    }
    assert _is_realtime_tool_turn(state) is True


def test_realtime_tool_turn_for_search_affirm_followup():
    from agent.stream_chat import _is_realtime_tool_turn

    history = [
        {"role": "user", "content": "长鑫存储今日财报"},
        {"role": "assistant", "content": "需要我查吗？我可以帮你上网搜索一下"},
    ]
    state = {"question": "需要", "turn_meta": {"query_intent": "kb"}}
    assert _is_realtime_tool_turn(state, history) is True
