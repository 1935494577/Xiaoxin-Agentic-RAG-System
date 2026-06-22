"""Domain term embedding neighbors for synonym / paraphrase expansion (Tier 2)."""

from __future__ import annotations

from typing import Any

import numpy as np

from config import settings
from indexing.embeddings import embed_texts
from retrieval.domain_lexicon import list_domain_terms, load_domain_lexicon

_cache: dict[str, Any] = {"updated_at": "", "terms": [], "matrix": None}


def invalidate_term_embedding_cache() -> None:
    _cache["updated_at"] = ""
    _cache["terms"] = []
    _cache["matrix"] = None


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na <= 0 or nb <= 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _ensure_term_matrix() -> tuple[list[str], np.ndarray] | None:
    if not bool(getattr(settings, "domain_embedding_neighbors_enabled", True)):
        return None
    data = load_domain_lexicon()
    updated = str(data.get("updated_at") or "")
    terms = list_domain_terms(limit=int(getattr(settings, "domain_embedding_max_terms", 2000)))
    if not terms:
        return None
    if _cache["updated_at"] == updated and _cache["matrix"] is not None and _cache["terms"] == terms:
        return _cache["terms"], _cache["matrix"]
    mat = embed_texts(terms)
    _cache["updated_at"] = updated
    _cache["terms"] = terms
    _cache["matrix"] = mat
    return terms, mat


def _term_related_to_query(query: str, term: str) -> bool:
    q_chars = {c for c in query if "\u4e00" <= c <= "\u9fff"}
    t_chars = {c for c in term if "\u4e00" <= c <= "\u9fff"}
    if not q_chars or not t_chars:
        return False
    overlap = q_chars & t_chars
    return len(overlap) >= min(2, len(t_chars), len(q_chars))


def nearest_domain_terms(
    query: str,
    *,
    top_k: int | None = None,
    min_sim: float | None = None,
) -> list[str]:
    """Return lexicon terms semantically close to query (excluding exact query)."""
    q = (query or "").strip()
    if not q:
        return []
    packed = _ensure_term_matrix()
    if not packed:
        return []
    terms, mat = packed
    k = top_k if top_k is not None else int(getattr(settings, "domain_embedding_neighbor_top_k", 2))
    floor = min_sim if min_sim is not None else float(getattr(settings, "domain_embedding_neighbor_min_sim", 0.72))
    q_vec = embed_texts([q])[0]
    scored: list[tuple[float, str]] = []
    for i, term in enumerate(terms):
        if term == q or term in q:
            continue
        if not _term_related_to_query(q, term):
            continue
        sim = _cosine_sim(q_vec, mat[i])
        if sim >= floor:
            scored.append((sim, term))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [t for _, t in scored[: max(1, k)]]


def expand_query_with_embedding_neighbors(text: str) -> list[str]:
    """Extra search variants from embedding nearest neighbors."""
    base = (text or "").strip()
    if not base:
        return []
    neighbors = nearest_domain_terms(base)
    out: list[str] = []
    for term in neighbors:
        variant = f"{base} {term}".strip() if term not in base else term
        if variant and variant not in out:
            out.append(variant)
    return out


def warmup_term_embedding_cache(*, max_terms: int = 32) -> None:
    """Pre-build a small term matrix slice so first QU request avoids cold embed batch."""
    if not bool(getattr(settings, "domain_embedding_neighbors_enabled", True)):
        return
    terms = list_domain_terms(limit=max(1, max_terms))
    if not terms:
        return
    embed_texts(terms[:max_terms])
    _ensure_term_matrix()
