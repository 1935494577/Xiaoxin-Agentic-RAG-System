"""Persona presets and agent reasoning modes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.persona_presets import (  # noqa: E402
    DEFAULT_PERSONA_ID,
    apply_active_persona,
    get_persona_content,
    get_persona_slot_overrides,
    list_persona_presets_public,
)
from agent.prompt_engine import compose_system_prompt, default_prompt_slots  # noqa: E402
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
    assert "brain_evolution_analyst" in ids
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


def test_load_prompt_slots_reflects_saved_active_persona(tmp_path, monkeypatch):
    import json

    from api.prompt_config_store import load_prompt_slots, save_prompt_config
    from config import settings

    prompt_path = tmp_path / "prompt_config.json"
    monkeypatch.setattr("api.prompt_config_store._config_path", lambda: prompt_path)
    monkeypatch.setattr(settings, "prompt_config_path", prompt_path)

    save_prompt_config(slots=[], reset_defaults=True, active_persona_id="reading_coach")
    slots = load_prompt_slots()
    persona = next(s for s in slots if s["id"] == "persona")
    assert "超脑阅读教练" in persona["content"]


def test_brain_evolution_analyst_applies_full_prompt_bundle():
    slots = apply_active_persona(default_prompt_slots(), "brain_evolution_analyst")
    persona = next(s for s in slots if s["id"] == "persona")
    kb_task = next(s for s in slots if s["id"] == "kb_task")
    output = next(s for s in slots if s["id"] == "output_style")
    assert "资深分析师" in persona["content"]
    assert "五种核心大脑能力" in persona["content"]
    assert "结构化输出" in kb_task["content"]
    assert "你可以试试" in output["content"]
    overrides = get_persona_slot_overrides("brain_evolution_analyst")
    assert "kb_policy" in overrides
    assert "kb_task_fast" in overrides


def test_brain_evolution_analyst_compose_kb_system_prompt():
    slots = apply_active_persona(default_prompt_slots(), "brain_evolution_analyst")
    composed = compose_system_prompt(slots, mode="kb", fast=False)
    assert "脑进化之书" in composed
    assert "延伸解读" in composed
    assert "直接回应" in composed


def test_answer_node_general_includes_direct_reasoning_policy(monkeypatch):
    from agent.nodes import answer_node
    from agent.prompt_engine import default_prompt_slots

    captured: dict = {}

    class _Msg:
        content = "好的"

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, **kwargs):
            pass

        chat = _Chat()

    monkeypatch.setattr("agent.nodes.OpenAI", lambda **kwargs: _Client())

    answer_node(
        {
            "question": "你好",
            "contexts": [],
            "contexts_meta": [],
            "history": [],
            "memory_config": {
                "prompt_slots": default_prompt_slots(),
                "agent_reasoning_mode": "direct",
                "general_fallback_enabled": False,
                "kb_llm_judge": False,
            },
            "llm_api_key": "sk-test",
        }
    )

    system = captured["messages"][0]["content"]
    assert "直接回答" in system
