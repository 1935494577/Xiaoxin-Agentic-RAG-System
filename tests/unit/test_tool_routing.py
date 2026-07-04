"""Tool routing for realtime queries and noisy voice input."""

from __future__ import annotations

import pytest

from agent.tools.runtime.routing import (
    normalize_tool_routing_question,
    question_needs_realtime_tools,
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
