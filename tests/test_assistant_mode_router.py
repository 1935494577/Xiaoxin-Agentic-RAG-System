"""Assistant mode → runtime profile mapping."""

from __future__ import annotations

from agent.runtime.modes import build_mode_profile, normalize_assistant_mode
from agent.runtime.router import apply_mode_to_memory, resolve_effective_mode


def test_normalize_assistant_mode_defaults_to_auto():
    assert normalize_assistant_mode(None) == "auto"
    assert normalize_assistant_mode("") == "auto"
    assert normalize_assistant_mode("invalid") == "auto"


def test_knowledge_mode_profile():
    profile = build_mode_profile("knowledge", {})
    assert profile.mode == "knowledge"
    assert profile.hybrid_expert_mode is False
    assert profile.rag_architecture == "auto"
    assert profile.agent_reasoning_mode == "direct"
    assert profile.stream_fast_mode is True
    assert profile.force_tools is False


def test_task_mode_profile():
    profile = build_mode_profile("task", {})
    assert profile.mode == "task"
    assert profile.hybrid_expert_mode is True
    assert profile.rag_architecture == "agentic"
    assert profile.agent_reasoning_mode == "react"
    assert profile.stream_fast_mode is False
    assert profile.force_tools is True


def test_auto_mode_profile_uses_ui_defaults():
    ui = {"default_assistant_mode": "auto", "hybrid_expert_mode": True}
    profile = build_mode_profile("auto", ui)
    assert profile.mode == "auto"
    assert profile.hybrid_expert_mode is None
    assert profile.rag_architecture is None
    assert profile.agent_reasoning_mode is None
    assert profile.force_tools is False


def test_resolve_effective_mode_request_over_ui():
    assert resolve_effective_mode("task", {"default_assistant_mode": "knowledge"}) == "task"


def test_apply_mode_to_memory_task():
    mem = {"agent_reasoning_mode": "direct"}
    profile = build_mode_profile("task", {})
    out = apply_mode_to_memory(mem, profile)
    assert out["agent_reasoning_mode"] == "react"
    assert out["_assistant_mode"] == "task"
    assert out["_assistant_force_tools"] is True


def test_pick_hybrid_expert_from_profile_not_request():
    from agent.runtime.router import pick_hybrid_expert_mode

    knowledge = build_mode_profile("knowledge", {})
    assert pick_hybrid_expert_mode(knowledge, ui_default=True) is False

    task = build_mode_profile("task", {})
    assert pick_hybrid_expert_mode(task, ui_default=False) is True

    auto = build_mode_profile("auto", {})
    assert pick_hybrid_expert_mode(auto, ui_default=True) is True
    assert pick_hybrid_expert_mode(auto, ui_default=False) is False
