"""L3 retrieval dedup: parent_id collapse, text similarity, MMR diversification."""

from __future__ import annotations

from typing import Any, Callable

from config import settings
from indexing.chunk_dedup_store import get_chunk_dedup_store
from indexing.dedup_text import char_ngram_jaccard


def _enrich_alias_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not settings.ingest_chunk_dedup_enabled:
        return rows
    store = get_chunk_dedup_store()
    out: list[dict[str, Any]] = []
    for row in rows:
        pid = str(row.get("parent_id") or "")
        aliases = store.aliases_for_parent(pid) if pid else []
        enriched = dict(row)
        if aliases:
            enriched["alias_sources"] = aliases
            base = str(row.get("source") or "")
            if base:
                merged = [base] + [a for a in aliases if a != base]
                enriched["source"] = " / ".join(dict.fromkeys(merged))
        out.append(enriched)
    return out


def _score(row: dict[str, Any]) -> float:
    for key in ("rerank_score", "hybrid_score", "score"):
        val = row.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def _text_similarity(a: str, b: str) -> float:
    return char_ngram_jaccard(a, b)


def deduplicate_by_parent_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        pid = str(row.get("parent_id") or "")
        if pid and pid in seen:
            continue
        if pid:
            seen.add(pid)
        out.append(row)
    return out


def deduplicate_by_text_similarity(
    rows: list[dict[str, Any]],
    *,
    threshold: float | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Keep highest-scored row when text similarity exceeds threshold."""
    limit = threshold if threshold is not None else settings.retrieval_dedup_similarity
    kept: list[dict[str, Any]] = []
    removed = 0
    for row in rows:
        text = str(row.get("text") or "")
        if not text:
            kept.append(row)
            continue
        dup = False
        for existing in kept:
            if _text_similarity(text, str(existing.get("text") or "")) >= limit:
                dup = True
                removed += 1
                break
        if not dup:
            kept.append(row)
    return kept, removed


def mmr_select(
    rows: list[dict[str, Any]],
    top_k: int,
    *,
    lambda_param: float | None = None,
    similarity_fn: Callable[[str, str], float] | None = None,
) -> list[dict[str, Any]]:
    """Maximal Marginal Relevance re-ranking on hybrid/rerank score."""
    lam = lambda_param if lambda_param is not None else settings.retrieval_mmr_lambda
    sim_fn = similarity_fn or _text_similarity
    if not rows or top_k <= 0:
        return []
    pool = list(rows)
    selected: list[dict[str, Any]] = []
    while pool and len(selected) < top_k:
        if not selected:
            selected.append(pool.pop(0))
            continue
        best_idx = 0
        best_mmr = float("-inf")
        for i, cand in enumerate(pool):
            rel = _score(cand)
            max_sim = max(
                sim_fn(str(cand.get("text") or ""), str(s.get("text") or ""))
                for s in selected
            )
            mmr = lam * rel - (1.0 - lam) * max_sim
            if mmr > best_mmr:
                best_mmr = mmr
                best_idx = i
        selected.append(pool.pop(best_idx))
    return selected


def deduplicate_retrieval_results(
    rows: list[dict[str, Any]],
    *,
    top_k: int,
    enabled: bool | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Full L3 pipeline: parent_id → text similarity → MMR → alias enrichment.
    Returns (results, stats).
    """
    use = settings.retrieval_dedup_enabled if enabled is None else enabled
    stats = {"input": len(rows), "removed_text_dup": 0, "output": 0}
    if not rows:
        return [], stats
    if not use:
        out = _enrich_alias_sources(rows[:top_k])
        stats["output"] = len(out)
        return out, stats

    step1 = deduplicate_by_parent_id(rows)
    step2, removed = deduplicate_by_text_similarity(step1)
    stats["removed_text_dup"] = removed
    step3 = mmr_select(step2, top_k)
    out = _enrich_alias_sources(step3)
    stats["output"] = len(out)
    return out, stats
