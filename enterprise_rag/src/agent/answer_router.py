"""Decide kb (RAG) vs general answer — delegates to kb_judge."""

from __future__ import annotations

from typing import Any

from agent.kb_judge import resolve_answer_mode as _resolve

__all__ = ["resolve_answer_mode", "best_retrieval_score", "has_usable_context"]


def best_retrieval_score(contexts_meta: list[dict[str, Any]]) -> float:
    from agent.kb_judge import best_hybrid_score

    return best_hybrid_score(contexts_meta)


def has_usable_context(contexts: list[str], contexts_meta: list[dict[str, Any]]) -> bool:
    from agent.kb_judge import has_usable_context as _has

    return _has(contexts, contexts_meta)


def resolve_answer_mode(
    contexts: list[str],
    contexts_meta: list[dict[str, Any]],
    *,
    kb_min_score: float,
    general_fallback_enabled: bool,
    question: str = "",
    kb_min_rerank_score: float = 0.0,
    kb_llm_judge: bool = True,
    llm_runtime: dict[str, Any] | None = None,
) -> str:
    return _resolve(
        question,
        contexts,
        contexts_meta,
        kb_min_score=kb_min_score,
        kb_min_rerank_score=kb_min_rerank_score,
        kb_llm_judge=kb_llm_judge,
        general_fallback_enabled=general_fallback_enabled,
        llm_runtime=llm_runtime,
    )
