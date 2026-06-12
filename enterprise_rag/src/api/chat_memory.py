"""Load memory / routing settings for chat endpoints."""

from __future__ import annotations

from typing import Any

from api.ui_config_store import load_ui_config


def chat_memory_settings() -> dict[str, Any]:
    from api.prompt_config_store import load_prompt_slots

    ui = load_ui_config()
    return {
        "max_history_turns": int(ui.get("max_history_turns") or 6),
        "max_history_chars": int(ui.get("max_history_chars") or 6000),
        "kb_min_score": float(ui.get("kb_min_score") or 0.55),
        "kb_min_rerank_score": float(ui.get("kb_min_rerank_score") or 0.0),
        "kb_llm_judge": bool(ui.get("kb_llm_judge", True)),
        "citation_max_sources": int(ui.get("citation_max_sources") or 2),
        "citation_min_relative_score": float(ui.get("citation_min_relative_score") or 0.75),
        "general_fallback_enabled": bool(ui.get("general_fallback_enabled", True)),
        "kb_post_stream_fallback": bool(ui.get("kb_post_stream_fallback", False)),
        "stream_verifier_enabled": bool(ui.get("stream_verifier_enabled", False)),
        "graph_verifier_enabled": bool(ui.get("graph_verifier_enabled", False)),
        "long_term_memory_enabled": bool(ui.get("long_term_memory_enabled", True)),
        "prompt_slots": load_prompt_slots(),
    }
