"""Load memory / routing settings for chat endpoints."""

from __future__ import annotations

from typing import Any

from api.ui_config_store import load_ui_config


def chat_memory_settings() -> dict[str, Any]:
    ui = load_ui_config()
    return {
        "max_history_turns": int(ui.get("max_history_turns") or 6),
        "max_history_chars": int(ui.get("max_history_chars") or 6000),
        "kb_min_score": float(ui.get("kb_min_score") or 0.55),
        "kb_min_rerank_score": float(ui.get("kb_min_rerank_score") or 0.0),
        "kb_llm_judge": bool(ui.get("kb_llm_judge", True)),
        "general_fallback_enabled": bool(ui.get("general_fallback_enabled", True)),
        "stream_verifier_enabled": bool(ui.get("stream_verifier_enabled", True)),
        "long_term_memory_enabled": bool(ui.get("long_term_memory_enabled", True)),
    }
