"""Business scene presets — one-click UI/chat defaults (P0)."""

from __future__ import annotations

from typing import Any

ScenePresetId = str

SCENE_PRESETS: dict[str, dict[str, Any]] = {
    "kb_frontline": {
        "label": "一线 KB 问答",
        "description": "培训/制度单跳检索为主：仅知识库、直接回答、快速流式。适合 Chat 默认与一线老师。",
        "patch": {
            "hybrid_expert_mode": False,
            "general_fallback_enabled": False,
            "kb_post_stream_fallback": False,
            "agent_reasoning_mode": "direct",
            "stream_fast_mode": True,
            "rag_arch_router_enabled": True,
            "rag_arch_llm_fallback": False,
            "default_rag_architecture": "auto",
            "kb_llm_judge": True,
            "condense_llm_enabled": True,
        },
    },
    "internal_full": {
        "label": "内测 / 运营全功能",
        "description": "混合专家 + ReAct 工具 + 通用兜底；用于坏例分析、反馈闭环与复杂题。",
        "patch": {
            "hybrid_expert_mode": True,
            "general_fallback_enabled": True,
            "kb_post_stream_fallback": False,
            "agent_reasoning_mode": "react",
            "stream_fast_mode": False,
            "rag_arch_router_enabled": True,
            "rag_arch_llm_fallback": False,
            "default_rag_architecture": "auto",
            "kb_llm_judge": True,
            "condense_llm_enabled": True,
        },
    },
    "api_kb_only": {
        "label": "LAN / API 知识库专用",
        "description": "与一线 KB 相同策略；供 run-api-lan -KbOnly 与集成方默认。",
        "patch": {
            "hybrid_expert_mode": False,
            "general_fallback_enabled": False,
            "kb_post_stream_fallback": False,
            "agent_reasoning_mode": "direct",
            "stream_fast_mode": True,
            "rag_arch_router_enabled": True,
            "rag_arch_llm_fallback": False,
            "default_rag_architecture": "auto",
            "kb_llm_judge": True,
            "condense_llm_enabled": True,
        },
    },
}

DEFAULT_SCENE_PRESET: ScenePresetId = "kb_frontline"


def list_scene_presets_public() -> list[dict[str, str]]:
    return [
        {
            "id": pid,
            "label": str(meta.get("label") or pid),
            "description": str(meta.get("description") or ""),
        }
        for pid, meta in SCENE_PRESETS.items()
    ]


def scene_preset_patch(preset_id: str) -> dict[str, Any] | None:
    row = SCENE_PRESETS.get((preset_id or "").strip())
    if not row:
        return None
    patch = dict(row.get("patch") or {})
    patch["scene_preset"] = preset_id
    return patch


def apply_scene_preset(preset_id: str) -> dict[str, Any]:
    from api.ui_config_store import save_ui_config

    patch = scene_preset_patch(preset_id)
    if not patch:
        raise ValueError(f"unknown scene preset: {preset_id}")
    return save_ui_config(patch)
