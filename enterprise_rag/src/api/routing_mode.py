"""Per-request RAG vs general routing (混合专家模式).

混合专家两阶段策略（流式 /chat/stream）:
  1. 预路由 retrieve → 重排/LLM 判断 → kb | general
  2. KB 生成（混合模式开启时先缓冲，避免未命中时闪出 KB 文本）
  3. 后验 kb_miss 检测 → 静默切换 general 流式输出
  4. 引用门控：仅 kb 且非 miss 时附带 source_refs
"""

from __future__ import annotations

from typing import Any

from api.ui_config_store import load_ui_config


def resolve_hybrid_expert_mode(request_value: bool | None) -> bool:
    if request_value is not None:
        return bool(request_value)
    return bool(load_ui_config().get("hybrid_expert_mode", False))


def apply_hybrid_expert_memory(mem: dict[str, Any], hybrid_expert_mode: bool) -> dict[str, Any]:
    """ON: RAG first, then general when retrieval or answer misses. OFF: RAG only."""
    out = dict(mem)
    if hybrid_expert_mode:
        out["general_fallback_enabled"] = True
        out["kb_post_stream_fallback"] = True
    else:
        out["general_fallback_enabled"] = False
        out["kb_post_stream_fallback"] = False
    return out
