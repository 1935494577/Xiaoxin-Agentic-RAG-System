"""Pipeline helpers for multi-architecture retrieval."""

from __future__ import annotations

from typing import Any

from agent.context_format import format_context_with_meta
from agent.nodes import retrieve_node
from graph.retrieve import graph_expand_retrieval, rrf_fuse_parents
from retrieval.hybrid_searcher import hybrid_search
from security.permissions import filter_by_sources


def run_classic_retrieval(state: dict[str, Any]) -> dict[str, Any]:
    return retrieve_node(state)  # type: ignore[arg-type]


def run_graph_retrieval(state: dict[str, Any]) -> dict[str, Any]:
    """Hybrid search + graph expand, fused via RRF."""
    dept = state.get("user_department") or "general"
    search_q = (state.get("retrieval_query") or state["question"]).strip()
    rk = state.get("rerank_top_k")
    rerank_k = int(rk) if rk is not None else None

    turn_meta = state.get("turn_meta") or {}
    retrieval_mode = (
        str(state.get("retrieval_mode") or turn_meta.get("retrieval_mode") or "").strip() or None
    )
    retrieval_meta: dict[str, Any] = {}
    rw, hybrid_parents = hybrid_search(
        search_q,
        dept,
        top_k=int(rerank_k) if rerank_k is not None else None,
        chat_model=state.get("chat_model"),
        llm_api_base=state.get("llm_api_base"),
        llm_api_key=state.get("llm_api_key"),
        llm_max_tokens_rewrite=state.get("llm_max_tokens_rewrite"),
        llm_extra_headers=state.get("llm_extra_headers"),
        skip_query_rewrite=bool(state.get("skip_retrieval_rewrite") or state.get("skip_query_rewrite")),
        retrieve_top_k=state.get("retrieve_top_k"),
        skip_rerank=bool(state.get("skip_rerank")),
        rerank_top_k=rerank_k,
        pre_rerank_k=state.get("pre_rerank_k"),
        retrieval_mode=retrieval_mode,  # type: ignore[arg-type]
        fast_mode=bool(state.get("stream_fast_mode")),
        retrieval_meta_out=retrieval_meta,
    )

    graph_parents = graph_expand_retrieval(search_q, dept)
    top_k = int(rerank_k) if rerank_k else 5
    parents = rrf_fuse_parents(hybrid_parents, graph_parents, top_k=top_k)
    parents = filter_by_sources(parents, state.get("allowed_sources"))

    max_chars = state.get("context_max_chars")
    if max_chars and int(max_chars) > 0:
        limit = int(max_chars)
        for p in parents:
            text = str(p.get("text") or "")
            if len(text) > limit:
                p["text"] = text[:limit] + "…"

    return {
        "rewritten_query": rw,
        "contexts": [format_context_with_meta(p) for p in parents],
        "contexts_meta": parents,
        "retrieval_meta": retrieval_meta,
    }
