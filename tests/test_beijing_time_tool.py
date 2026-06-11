"""Tests for Beijing time tool and realtime question routing."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.prompt_engine import compose_system_prompt, default_prompt_slots  # noqa: E402
from agent.tools.builtins.datetime_cn import get_beijing_time  # noqa: E402
from agent.tools.config.registry import TOOL_DEFINITIONS  # noqa: E402
from agent.tools.runtime.routing import question_needs_agent_tools  # noqa: E402


def test_registry_includes_get_beijing_time():
    assert "get_beijing_time" in TOOL_DEFINITIONS


def test_get_beijing_time_format(monkeypatch):
    fixed = datetime(2026, 6, 11, 15, 30, 45, tzinfo=ZoneInfo("Asia/Shanghai"))

    class _FixedDatetime:
        @classmethod
        def now(cls, tz=None):
            return fixed

    monkeypatch.setattr("agent.tools.builtins.datetime_cn.datetime", _FixedDatetime)
    out = get_beijing_time()
    assert "2026年06月11日" in out
    assert "星期四" in out
    assert "15:30:45" in out
    assert "北京时间" in out


@pytest.mark.parametrize(
    "q",
    [
        "今天是哪一年，哪一月",
        "现在几点了",
        "2026年春节放假安排",
        "杭州今天天气怎么样",
    ],
)
def test_question_needs_agent_tools_true(q: str):
    assert question_needs_agent_tools(q) is True


@pytest.mark.parametrize(
    "q",
    [
        "1-3年级超脑阅读要求是什么",
        "什么是 RAG",
        "介绍一下爱因斯坦",
    ],
)
def test_question_needs_agent_tools_false(q: str):
    assert question_needs_agent_tools(q) is False


def test_general_prompt_requires_tools_not_hallucinate():
    text = compose_system_prompt(default_prompt_slots(), mode="general", fast=False)
    assert "必须先调用" in text or "必须调用" in text
    assert "禁止" in text
    assert "get_beijing_time" in text
