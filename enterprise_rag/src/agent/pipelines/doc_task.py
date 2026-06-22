"""Document task pipelines: summary, extract, compare, annotate."""

from __future__ import annotations

from typing import Any

from agent.context_format import format_context_with_meta
from chat_ephemeral.store import search_ephemeral
from indexing.es_indexer import fetch_parents_by_ids


def retrieve_for_doc_task(
    state: dict[str, Any],
    *,
    input_mode: str,
    doc_task_type: str | None,
) -> dict[str, Any]:
    """Load contexts for whole-document tasks."""
    session_id = str(state.get("session_id") or "")
    temp_doc_id = str(state.get("temp_document_id") or "")
    allowed = state.get("allowed_sources") or []
    question = state.get("question") or ""

    if input_mode == "temp_document" and session_id and temp_doc_id:
        parents = search_ephemeral(session_id, temp_doc_id, question, top_k=12)
        return {
            "rewritten_query": question,
            "contexts": [format_context_with_meta(p) for p in parents],
            "contexts_meta": parents,
        }

    if allowed:
        # Pull all parents for listed sources via BM25 fetch by broad query
        from retrieval.hybrid_searcher import hybrid_search

        dept = state.get("user_department") or "general"
        rw, parents = hybrid_search(
            question or " ".join(allowed),
            dept,
            top_k=12 if doc_task_type != "compare" else 16,
            chat_model=state.get("chat_model"),
            llm_api_base=state.get("llm_api_base"),
            llm_api_key=state.get("llm_api_key"),
            skip_query_rewrite=True,
        )
        parents = [p for p in parents if str(p.get("source") or "") in set(allowed)]
        return {
            "rewritten_query": rw,
            "contexts": [format_context_with_meta(p) for p in parents],
            "contexts_meta": parents,
        }

    return {"rewritten_query": question, "contexts": [], "contexts_meta": []}
