from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from config import settings
from indexing.embeddings import embed_texts
from indexing.es_indexer import bm25_parent_search, fetch_parents_by_ids
from indexing.milvus_indexer import vector_search
from retrieval.query_rewriter import rewrite_query
from retrieval.reranker import rerank_parents
from retrieval.result_dedup import deduplicate_retrieval_results
from chunker.utils import tags_from_store_value


def _norm_map(scores: dict[str, float], higher_is_better: bool) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    out: dict[str, float] = {}
    for k, s in scores.items():
        if hi == lo:
            out[k] = 1.0
        elif higher_is_better:
            out[k] = (s - lo) / (hi - lo) if hi != lo else 1.0
        else:
            out[k] = (hi - s) / (hi - lo) if hi != lo else 1.0
    return out


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
) -> tuple[str, list[dict[str, Any]]]:
    """
    步骤4：改写 → Milvus(部门过滤) + 本地 rank-bm25 父块 → 按 parent_id 融合 → Rerank → Top 父块。
    返回 (rewritten_query, parents)。
    """
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
    q_emb = embed_texts([rewritten])[0].tolist()

    dept = user_department or None
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_vec = pool.submit(vector_search, q_emb, rk, user_department=dept)
        f_bm25 = pool.submit(bm25_parent_search, rewritten, rk)
        vec_hits = f_vec.result()
        es_hits = f_bm25.result()

    v_score: dict[str, float] = defaultdict(float)
    for h in vec_hits:
        pid = str(h.get("parent_id") or "")
        if not pid:
            continue
        v_score[pid] = max(v_score[pid], float(h.get("score", 0.0)))

    e_score: dict[str, float] = {}
    e_row: dict[str, dict[str, Any]] = {}
    for h in es_hits:
        pid = str(h.get("parent_id") or "")
        if not pid:
            continue
        e_score[pid] = max(e_score.get(pid, 0.0), float(h.get("score", 0.0)))
        e_row[pid] = h

    v_n = _norm_map(dict(v_score), higher_is_better=True)
    e_n = _norm_map(e_score, higher_is_better=True)

    all_pids = set(v_n) | set(e_n)
    combined: dict[str, float] = {}
    wv, wb = settings.hybrid_vector_weight, settings.hybrid_bm25_weight
    for pid in all_pids:
        combined[pid] = wv * v_n.get(pid, 0.0) + wb * e_n.get(pid, 0.0)

    missing = [pid for pid in all_pids if pid not in e_row]
    fetched = fetch_parents_by_ids(missing)

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
        if not text and pid in v_score:
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

    final_k = rerank_top_k if rerank_top_k is not None else settings.rerank_top_k
    dedup_pool = final_k * 3 if (retrieval_dedup if retrieval_dedup is not None else settings.retrieval_dedup_enabled) else final_k

    if skip_rerank:
        ranked, _ = deduplicate_retrieval_results(
            candidates[:dedup_pool],
            top_k=final_k,
            enabled=retrieval_dedup,
        )
        return rewritten, ranked

    cap = pre_rerank_k if pre_rerank_k is not None else min(len(candidates), max(final_k * 2, dedup_pool))
    pool = candidates[: max(final_k, cap)]
    ranked = rerank_parents(query, pool, top_k=min(len(pool), dedup_pool))
    deduped, _ = deduplicate_retrieval_results(ranked, top_k=final_k, enabled=retrieval_dedup)
    return rewritten, deduped
