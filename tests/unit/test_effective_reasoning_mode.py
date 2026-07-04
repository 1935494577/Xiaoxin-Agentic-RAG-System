"""Effective reasoning mode resolver for KB-only vs hybrid paths."""

from __future__ import annotations

from api.ui_config_store import resolve_effective_reasoning_mode


def test_kb_only_upgrades_react_to_direct():
    ui = {"hybrid_expert_mode": False, "agent_reasoning_mode": "react"}
    assert resolve_effective_reasoning_mode(ui) == "direct"


def test_kb_only_keeps_direct():
    ui = {"hybrid_expert_mode": False, "agent_reasoning_mode": "direct"}
    assert resolve_effective_reasoning_mode(ui) == "direct"


def test_hybrid_keeps_react():
    ui = {"hybrid_expert_mode": True, "agent_reasoning_mode": "react"}
    assert resolve_effective_reasoning_mode(ui) == "react"


def test_hybrid_keeps_plan_execute():
    ui = {"hybrid_expert_mode": True, "agent_reasoning_mode": "plan_execute"}
    assert resolve_effective_reasoning_mode(ui) == "plan_execute"


def test_hybrid_expert_override():
    ui = {"hybrid_expert_mode": True, "agent_reasoning_mode": "react"}
    assert resolve_effective_reasoning_mode(ui, hybrid_expert=False) == "direct"
