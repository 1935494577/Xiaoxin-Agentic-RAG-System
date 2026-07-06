"""DF-4 routing: task/auto → Jnao lead when harness available."""

from __future__ import annotations

from jnao_harness.availability import resolve_assistant_mode, should_use_agent_lead


def test_task_mode_uses_agent_lead_when_harness_available(monkeypatch):
    monkeypatch.setattr(
        "jnao_harness.availability.harness_available",
        lambda: True,
    )
    state = {"assistant_mode": "task", "question": "2025年AI发展"}
    assert should_use_agent_lead(state) is True


def test_knowledge_mode_never_uses_agent_lead(monkeypatch):
    monkeypatch.setattr(
        "jnao_harness.availability.harness_available",
        lambda: True,
    )
    state = {"assistant_mode": "knowledge", "question": "超脑阅读"}
    assert should_use_agent_lead(state) is False


def test_auto_mode_uses_deerflow_when_harness_available(monkeypatch):
    monkeypatch.setattr(
        "jnao_harness.availability.harness_available",
        lambda: True,
    )
    assert should_use_agent_lead({"assistant_mode": "auto"}) is True


def test_resolve_assistant_mode_from_memory_config():
    state = {"memory_config": {"_assistant_mode": "task"}}
    assert resolve_assistant_mode(state) == "task"
