"""Exam scene presets — TDD."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_exam_assemble_scene_preset_listed():
    from api.scene_presets import SCENE_PRESETS, list_scene_presets_public, scene_preset_patch

    assert "exam_assemble" in SCENE_PRESETS
    assert "exam_lesson" in SCENE_PRESETS
    assert "exam_ingest" in SCENE_PRESETS
    ids = {x["id"] for x in list_scene_presets_public()}
    assert "exam_assemble" in ids
    patch = scene_preset_patch("exam_assemble")
    assert patch is not None
    assert patch["scene_preset"] == "exam_assemble"
    assert patch.get("hybrid_expert_mode") is False
