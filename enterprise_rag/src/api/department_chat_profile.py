"""Per-department Chat behavior — content teams get analyst features without Admin access."""

from __future__ import annotations

from typing import Any

from api.scene_presets import scene_preset_patch
from security.department_features import normalize_department, should_enforce_department

# 运营 / 媒体 / 剪辑：登录部门自动套用 analyst 的对话能力（无需进「对话设置」）
DEPARTMENT_CHAT_PRESET: dict[str, str] = {
    "运营部": "analyst",
    "媒体部": "analyst",
    "剪辑部": "analyst",
}

# 只覆盖与内容场景相关的项；混合专家仍由 Chat 页开关 / UI 默认决定
_PRESET_KEYS = (
    "clarify_enabled",
    "agent_reasoning_mode",
    "stream_fast_mode",
    "general_fallback_enabled",
    "kb_post_stream_fallback",
    "rag_arch_router_enabled",
    "rag_arch_llm_fallback",
    "default_rag_architecture",
    "kb_llm_judge",
    "condense_llm_enabled",
)


def department_chat_preset_id(department: str | None) -> str | None:
    dept = normalize_department(department)
    if not dept or not should_enforce_department(dept):
        return None
    return DEPARTMENT_CHAT_PRESET.get(dept)


def apply_department_chat_profile(
    mem: dict[str, Any],
    department: str | None,
) -> dict[str, Any]:
    preset_id = department_chat_preset_id(department)
    if not preset_id:
        return mem
    patch = scene_preset_patch(preset_id)
    if not patch:
        return mem
    out = dict(mem)
    for key in _PRESET_KEYS:
        if key in patch:
            out[key] = patch[key]
    out["department_chat_preset"] = preset_id
    return out
