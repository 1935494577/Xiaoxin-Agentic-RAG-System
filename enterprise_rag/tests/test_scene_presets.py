"""Scene preset one-click UI defaults."""

from __future__ import annotations

import pytest

from api.scene_presets import (
    DEFAULT_SCENE_PRESET,
    SCENE_PRESETS,
    apply_scene_preset,
    list_scene_presets_public,
    scene_preset_patch,
)


def test_list_scene_presets_public():
    rows = list_scene_presets_public()
    assert len(rows) == len(SCENE_PRESETS)
    ids = {r["id"] for r in rows}
    assert ids == set(SCENE_PRESETS.keys())


def test_kb_frontline_preset_kb_only_direct():
    patch = scene_preset_patch("kb_frontline")
    assert patch is not None
    assert patch["hybrid_expert_mode"] is False
    assert patch["general_fallback_enabled"] is False
    assert patch["agent_reasoning_mode"] == "direct"
    assert patch["stream_fast_mode"] is True
    assert patch["scene_preset"] == "kb_frontline"


def test_internal_full_preset_hybrid_react():
    patch = scene_preset_patch("internal_full")
    assert patch is not None
    assert patch["hybrid_expert_mode"] is True
    assert patch["agent_reasoning_mode"] == "react"
    assert patch["stream_fast_mode"] is False


def test_unknown_preset_returns_none():
    assert scene_preset_patch("missing") is None


def test_apply_scene_preset_persists(tmp_path, monkeypatch):
    ui_path = tmp_path / "ui_config.json"
    monkeypatch.setattr("api.ui_config_store._config_path", lambda: ui_path)
    from config import settings

    monkeypatch.setattr(settings, "ui_config_path", ui_path)

    cfg = apply_scene_preset("internal_full")
    assert cfg["scene_preset"] == "internal_full"
    assert cfg["hybrid_expert_mode"] is True
    assert ui_path.is_file()

    cfg2 = apply_scene_preset(DEFAULT_SCENE_PRESET)
    assert cfg2["hybrid_expert_mode"] is False
    assert cfg2["agent_reasoning_mode"] == "direct"
