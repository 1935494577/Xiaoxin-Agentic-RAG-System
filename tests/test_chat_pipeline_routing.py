"""Tests for chat pipeline routing (DeerFlow lead vs KB fast path)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _reset_lead_flag(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "chat_lead_agent_enabled", True)


def test_knowledge_mode_uses_kb_fast_path(monkeypatch):
    from jnao_harness import availability

    monkeypatch.setattr(availability, "harness_available", lambda: True)
    state = {"assistant_mode": "knowledge"}
    assert availability.resolve_chat_pipeline(state) == "kb_fast"
    assert availability.should_use_agent_lead(state) is False


def test_task_mode_uses_lead_when_harness_present(monkeypatch):
    from jnao_harness import availability

    monkeypatch.setattr(availability, "harness_available", lambda: True)
    state = {"assistant_mode": "task"}
    assert availability.resolve_chat_pipeline(state) == "lead_agent"
    assert availability.should_use_agent_lead(state) is True


def test_lead_disabled_falls_back_to_kb(monkeypatch):
    from config import settings
    from jnao_harness import availability

    monkeypatch.setattr(settings, "chat_lead_agent_enabled", False)
    monkeypatch.setattr(availability, "harness_available", lambda: True)
    state = {"assistant_mode": "task"}
    assert availability.resolve_chat_pipeline(state) == "kb_fast"
