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
