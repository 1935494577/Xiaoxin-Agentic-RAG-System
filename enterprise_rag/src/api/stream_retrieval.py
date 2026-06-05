"""Stream chat retrieval profiles: standard (quality) vs fast (low latency)."""

from __future__ import annotations

from typing import Any

from api.ui_config_store import load_ui_config
from config import settings


def resolve_stream_fast_mode(request_value: bool | None) -> bool:
    if request_value is not None:
        return bool(request_value)
    return bool(load_ui_config().get("stream_fast_mode", False))


def build_stream_retrieval_state(
    fast: bool,
    *,
    skip_query_rewrite: bool | None = None,
) -> dict[str, Any]:
    """Standard = previous streaming behavior; fast = optimized path."""
    sq = True if skip_query_rewrite is None else skip_query_rewrite
    if fast:
        return {
            "stream_fast_mode": True,
            "skip_query_rewrite": sq,
            "retrieve_top_k": settings.stream_retrieve_top_k,
            "rerank_top_k": settings.stream_rerank_top_k,
            "skip_rerank": settings.stream_skip_rerank,
            "pre_rerank_k": settings.stream_pre_rerank_k,
            "context_max_chars": settings.stream_context_max_chars,
        }
    return {
        "stream_fast_mode": False,
        "skip_query_rewrite": sq,
        "retrieve_top_k": settings.stream_standard_retrieve_top_k,
        "rerank_top_k": settings.rerank_top_k,
        "skip_rerank": False,
        "pre_rerank_k": None,
        "context_max_chars": 0,
    }
