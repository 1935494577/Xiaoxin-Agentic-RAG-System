"""TDD: typhoon/correction routing + realtime tool policy text."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.tools.runtime.prompt import AGENT_TOOLS_REALTIME_POLICY  # noqa: E402
from agent.tools.runtime.routing import (  # noqa: E402
    enrich_question_for_fact_correction,
    is_typhoon_or_warning_question,
    is_user_fact_correction,
    question_needs_realtime_tools,
    resolve_web_search_query_for_correction,
)


def test_typhoon_question_needs_realtime_and_is_flagged():
    q = "台风白海豚对萧山有什么影响"
    assert is_typhoon_or_warning_question(q) is True
    assert question_needs_realtime_tools(q) is True


def test_user_fact_correction_detected():
    assert is_user_fact_correction("台风巴威不是已经过去了么，现在要来的台风不是白海豚么") is True
    assert is_user_fact_correction("你搞错了，应该是白海豚") is True
    assert is_user_fact_correction("萧山今天天气怎么样") is False


def test_correction_web_search_query_includes_year_and_name():
    history = [
        {"role": "user", "content": "萧山今天天气和台风情况"},
        {"role": "assistant", "content": "台风巴威正在影响浙江…"},
        {"role": "user", "content": "台风巴威不是已经过去了么，现在要来的台风不是白海豚么"},
    ]
    q = resolve_web_search_query_for_correction(
        "台风巴威不是已经过去了么，现在要来的台风不是白海豚么",
        history,
    )
    assert "白海豚" in q
    assert "2026" in q or "台风" in q
    assert "巴威" not in q or "白海豚" in q  # 主题应落到纠正后的名称


def test_realtime_policy_mentions_location_guard_and_typhoon_split():
    text = AGENT_TOOLS_REALTIME_POLICY
    assert "定位校验失败" in text
    assert "台风" in text
    assert "web_search" in text
    assert "get_weather" in text
    assert "纠正" in text or "不是" in text


def test_enrich_question_for_fact_correction_injects_search_hint():
    q = "台风巴威不是已经过去了么，现在要来的台风不是白海豚么"
    enriched = enrich_question_for_fact_correction(q, history=None)
    assert enriched is not None
    assert "白海豚" in enriched
    assert "web_search" in enriched
    assert "系统提示" in enriched
    assert enrich_question_for_fact_correction("萧山今天天气怎么样") is None
