"""Department-based Chat profile overlay for content teams."""

from __future__ import annotations

from api.department_chat_profile import (
    apply_department_chat_profile,
    department_chat_preset_id,
)
from api.scene_presets import scene_preset_patch


def test_ops_department_gets_analyst_preset_id():
    assert department_chat_preset_id("运营部") == "analyst"
    assert department_chat_preset_id("技术部") is None


def test_apply_department_chat_profile_enables_clarify():
    base = {"clarify_enabled": False, "agent_reasoning_mode": "direct"}
    out = apply_department_chat_profile(base, "运营部")
    assert out["clarify_enabled"] is True
    assert out["agent_reasoning_mode"] == "react"
    assert out["department_chat_preset"] == "analyst"


def test_tech_department_unchanged():
    base = {"clarify_enabled": False}
    assert apply_department_chat_profile(base, "技术部") == base


def test_analyst_patch_has_clarify():
    patch = scene_preset_patch("analyst")
    assert patch is not None
    assert patch.get("clarify_enabled") is True
