from __future__ import annotations

import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

from config import settings
from indexing.embeddings import embed_texts
from indexing.es_indexer import bm25_parent_search, fetch_parents_by_ids
from indexing.milvus_indexer import vector_search
from retrieval.query_rewriter import rewrite_query
from retrieval.reranker import rerank_parents
from retrieval.result_dedup import deduplicate_retrieval_results
from retrieval.search_cache import build_search_cache_key, get_search_cache
from chunker.utils import tags_from_store_value

_search_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hybrid-search")

RetrievalMode = Literal["exact", "semantic", "hybrid"]


def _rrf_k() -> int:
    try:
        from retrieval.retrieval_tuning_store import get_rrf_k

        return get_rrf_k()
    except Exception:
        return max(1, int(getattr(settings, "rrf_k", 60) or 60))


def _rrf_fuse(rankings: list[list[str]], *, k: int | None = None) -> dict[str, float]:
    kk = k if k is not None else _rrf_k()
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, pid in enumerate(ranking):
            if pid:
                scores[pid] += 1.0 / (kk + rank + 1)
    return dict(scores)


def _rank_from_scores(scores: dict[str, float]) -> list[str]:
    return [pid for pid, _ in sorted(scores.items(), key=lambda x: -x[1])]


def _scores_from_ranking(ranking: list[str], *, k: int | None = None) -> dict[str, float]:
    kk = k if k is not None else _rrf_k()
    return {pid: 1.0 / (kk + rank + 1) for rank, pid in enumerate(ranking) if pid}


def _parse_bm25_hits(es_hits: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    e_score: dict[str, float] = {}
    e_row: dict[str, dict[str, Any]] = {}
    for h in es_hits:
        pid = str(h.get("parent_id") or "")
        if not pid:
            continue
        e_score[pid] = max(e_score.get(pid, 0.0), float(h.get("score", 0.0)))
        e_row[pid] = h
    return e_score, e_row


def _parse_vector_hits(vec_hits: list[dict[str, Any]]) -> dict[str, float]:
    v_score: dict[str, float] = defaultdict(float)
    for h in vec_hits:
        pid = str(h.get("parent_id") or "")
        if pid:
            v_score[pid] = max(v_score[pid], float(h.get("score", 0.0)))
    return dict(v_score)


def _search_variant(
    mode: RetrievalMode,
    query: str,
    q_emb: list[float] | None,
    *,
    user_department: str | None,
    rk: int,
) -> tuple[dict[str, float], dict[str, dict[str, Any]], list[dict[str, Any]], list[str], float]:
    """Return fused scores, bm25 rows, vector hits, paths used, max bm25 score."""
    dept = user_department or None
    paths: list[str] = []
    max_bm25 = 0.0

    if mode == "exact":
        es_hits = bm25_parent_search(query, rk, user_department=dept)
        e_score, e_row = _parse_bm25_hits(es_hits)
        max_bm25 = max(e_score.values()) if e_score else 0.0
        ranking = _rank_from_scores(e_score)
        return _scores_from_ranking(ranking), e_row, [], ["bm25"], max_bm25

    if mode == "semantic":
        if q_emb is None:
            return {}, {}, [], ["vector"], 0.0
        vec_hits = vector_search(q_emb, rk, user_department=dept)
        v_score = _parse_vector_hits(vec_hits)
        ranking = _rank_from_scores(v_score)
        return _scores_from_ranking(ranking), {}, vec_hits, ["vector"], 0.0

    if q_emb is None:
        return {}, {}, [], ["bm25", "vector", "rrf"], 0.0
    f_vec = _search_pool.submit(vector_search, q_emb, rk, user_department=dept)
    f_bm25 = _search_pool.submit(bm25_parent_search, query, rk, user_department=dept)
    vec_hits = f_vec.result()
    es_hits = f_bm25.result()
    e_score, e_row = _parse_bm25_hits(es_hits)
    v_score = _parse_vector_hits(vec_hits)
    max_bm25 = max(e_score.values()) if e_score else 0.0
    fused = _rrf_fuse([_rank_from_scores(e_score), _rank_from_scores(v_score)])
    return fused, e_row, vec_hits, ["bm25", "vector", "rrf"], max_bm25


def _collect_candidates(
    combined: dict[str, float],
    *,
    e_row: dict[str, dict[str, Any]],
    vec_hits: list[dict[str, Any]],
    user_department: str,
    v_score_backup: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    missing = [pid for pid in combined if pid not in e_row]
    fetched = fetch_parents_by_ids(missing)
    v_backup = v_score_backup or {}

    candidates: list[dict[str, Any]] = []
    for pid, hy in sorted(combined.items(), key=lambda x: -x[1]):
        row = e_row.get(pid) or fetched.get(pid)
        text = ""
        department = user_department
        source = ""
        permission_label = ""
        tags: list[str] = []
        if row:
            text = str(row.get("text") or "")
            department = str(row.get("department") or department or "")
            source = str(row.get("source") or "")
            permission_label = str(row.get("permission_label") or "")
            raw_tags = row.get("tags")
            if isinstance(raw_tags, list):
                tags = [str(t) for t in raw_tags if str(t).strip()]
            elif raw_tags:
                tags = tags_from_store_value(str(raw_tags))
        if not text and (pid in v_backup or any(str(h.get("parent_id")) == pid for h in vec_hits)):
            vrows = [h for h in vec_hits if str(h.get("parent_id")) == pid]
            if vrows:
                text = "\n".join(str(h.get("text") or "") for h in vrows[:3])
                if not department:
                    department = str(vrows[0].get("department") or department or "")
                if not source:
                    source = str(vrows[0].get("source") or "")
                if not tags:
                    tags = tags_from_store_value(str(vrows[0].get("tags") or ""))
        candidates.append(
            {
                "parent_id": pid,
                "text": text,
                "department": department,
                "source": source,
                "permission_label": permission_label,
                "tags": tags,
                "hybrid_score": float(hy),
            }
        )
    return candidates


def hybrid_search(
    query: str,
    user_department: str,
    top_k: int = 5,
    chat_model: str | None = None,
    *,
    llm_api_base: str | None = None,
    llm_api_key: str | None = None,
    llm_max_tokens_rewrite: int | None = None,
    llm_extra_headers: dict[str, Any] | None = None,
    skip_query_rewrite: bool | None = None,
    retrieve_top_k: int | None = None,
    skip_rerank: bool = False,
    rerank_top_k: int | None = None,
    pre_rerank_k: int | None = None,
    retrieval_dedup: bool | None = None,
    retrieval_mode: RetrievalMode | None = None,
    fast_mode: bool = False,
    retrieval_meta_out: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    改写 → 按 retrieval_mode 选路 → BM25 / Vector / RRF → Rerank → Top 父块。
    返回 (rewritten_query, parents)。
    """
    from retrieval.retrieval_mode_router import resolve_retrieval_mode
    from security.access_control import normalize_department

    t0 = time.perf_counter()
    user_department = normalize_department(user_department)
    mode: RetrievalMode = retrieval_mode or resolve_retrieval_mode(
        query,
        fast_mode=fast_mode,
    )

    cache_params = {
        "top_k": top_k,
        "skip_query_rewrite": skip_query_rewrite,
        "retrieve_top_k": retrieve_top_k,
        "skip_rerank": skip_rerank,
        "rerank_top_k": rerank_top_k,
        "pre_rerank_k": pre_rerank_k,
        "retrieval_dedup": retrieval_dedup,
        "query_rewrite_enabled": settings.query_rewrite_enabled,
        "query_normalize_enabled": settings.query_normalize_enabled,
        "retrieval_mode": mode,
    }
    cache_key = build_search_cache_key(query, user_department, **cache_params)
    cache = get_search_cache()
    cached = cache.get(cache_key)
    if cached is not None:
        if retrieval_meta_out is not None:
            retrieval_meta_out.update(
                {
                    "retrieval_mode": mode,
                    "paths_used": ["cache"],
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "cache_hit": True,
                }
            )
        return cached

    do_rewrite = settings.query_rewrite_enabled if skip_query_rewrite is None else not skip_query_rewrite
    if do_rewrite:
        rewritten = rewrite_query(
            query,
            chat_model=chat_model,
            api_base=llm_api_base,
            api_key=llm_api_key,
            max_tokens=llm_max_tokens_rewrite,
            default_headers=llm_extra_headers,
        )
    else:
        rewritten = query

    rk = retrieve_top_k if retrieve_top_k is not None else settings.retrieve_top_k
    if mode == "exact":
        variants = [rewritten]
    elif settings.query_normalize_enabled:
        from retrieval.query_understanding import build_search_variants_enriched

        variants = build_search_variants_enriched(
            rewritten,
            max_variants=int(settings.query_normalize_max_variants),
        )
    else:
        variants = [rewritten]

    if not variants:
        if retrieval_meta_out is not None:
            retrieval_meta_out.update(
                {
                    "retrieval_mode": mode,
                    "paths_used": [],
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "cache_hit": False,
                }
            )
        cache.set(cache_key, rewritten, [])
        return rewritten, []

    embeddings: list[Any] = []
    if mode != "exact":
        embeddings = embed_texts(variants)

    rankings: list[list[str]] = []
    merged_e_row: dict[str, dict[str, Any]] = {}
    merged_vec_hits: list[dict[str, Any]] = []
    paths_used: set[str] = set()
    max_bm25_score = 0.0

    for idx, variant in enumerate(variants):
        q_emb = embeddings[idx].tolist() if idx < len(embeddings) else None
        combined, e_row, vec_hits, paths, bm25_top = _search_variant(
            mode,
            variant,
            q_emb,
            user_department=user_department or None,
            rk=rk,
        )
        paths_used.update(paths)
        max_bm25_score = max(max_bm25_score, bm25_top)
        ordered = [pid for pid, _ in sorted(combined.items(), key=lambda x: -x[1])]
        rankings.append(ordered)
        merged_e_row.update(e_row)
        merged_vec_hits.extend(vec_hits)

    if len(rankings) == 1:
        fused = _scores_from_ranking(rankings[0])
    else:
        fused = _rrf_fuse(rankings)
        paths_used.add("rrf")

    candidates = _collect_candidates(
        fused,
        e_row=merged_e_row,
        vec_hits=merged_vec_hits,
        user_department=user_department,
    )

    final_k = rerank_top_k if rerank_top_k is not None else settings.rerank_top_k
    dedup_pool = final_k * 3 if (retrieval_dedup if retrieval_dedup is not None else settings.retrieval_dedup_enabled) else final_k

    do_skip_rerank = skip_rerank
    if (
        not do_skip_rerank
        and mode == "exact"
        and bool(settings.exact_skip_rerank_enabled)
        and max_bm25_score >= float(settings.exact_skip_rerank_min_score)
    ):
        do_skip_rerank = True

    if do_skip_rerank:
        ranked, _ = deduplicate_retrieval_results(
            candidates[:dedup_pool],
            top_k=final_k,
            enabled=retrieval_dedup,
        )
        if retrieval_meta_out is not None:
            retrieval_meta_out.update(
                {
                    "retrieval_mode": mode,
                    "paths_used": sorted(paths_used),
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "cache_hit": False,
                    "skip_rerank": True,
                    "max_bm25_score": max_bm25_score,
                }
            )
        cache.set(cache_key, rewritten, ranked)
        return rewritten, ranked

    cap = pre_rerank_k if pre_rerank_k is not None else min(len(candidates), max(final_k * 2, dedup_pool))
    pool = candidates[: max(final_k, cap)]
    ranked = rerank_parents(query, pool, top_k=min(len(pool), dedup_pool))
    paths_used.add("rerank")
    deduped, _ = deduplicate_retrieval_results(ranked, top_k=final_k, enabled=retrieval_dedup)
    if retrieval_meta_out is not None:
        retrieval_meta_out.update(
            {
                "retrieval_mode": mode,
                "paths_used": sorted(paths_used),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                "cache_hit": False,
                "skip_rerank": False,
                "max_bm25_score": max_bm25_score,
            }
        )
    cache.set(cache_key, rewritten, deduped)
    return rewritten, deduped
