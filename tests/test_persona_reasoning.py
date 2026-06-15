"""Persona presets and agent reasoning modes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.persona_presets import (  # noqa: E402
    DEFAULT_PERSONA_ID,
    get_persona_content,
    list_persona_presets_public,
)
from agent.reasoning_modes import (  # noqa: E402
    normalize_reasoning_mode,
    reasoning_policy,
    should_use_tool_loop,
)


def test_persona_presets_include_legacy_and_brain_ed_roles():
    presets = list_persona_presets_public()
    ids = {p["id"] for p in presets}
    assert "legacy_assistant" in ids
    assert "knowledge_consultant" in ids
    assert "reading_coach" in ids
    assert DEFAULT_PERSONA_ID == "knowledge_consultant"


def test_get_persona_content_returns_brain_ed_copy():
    text = get_persona_content("parent_advisor")
    assert text
    assert "家长" in text
    assert "劲脑" in text


def test_reasoning_modes_normalize_and_policy():
    assert normalize_reasoning_mode("plan_execute") == "plan_execute"
    assert normalize_reasoning_mode("unknown") == "react"
    assert "ReAct" in reasoning_policy("react")
    assert "Plan-and-Execute" in reasoning_policy("plan_execute")


def test_should_use_tool_loop_direct_skips_tools():
    assert should_use_tool_loop("direct", tools_enabled=True) is False
    assert should_use_tool_loop("react", tools_enabled=True) is True
    assert should_use_tool_loop("react", tools_enabled=False) is False
