"""Graph-based retrieval: seed entities → expand → parent text."""

from __future__ import annotations

import re
from typing import Any

from graph.store import expand_from_seeds, list_entities_matching
from indexing.es_indexer import fetch_parents_by_ids


_ENTITY_SPLIT = re.compile(r"[、，,和与及\s]+")


def seed_entities_from_question(question: str) -> list[str]:
    q = (question or "").strip()
    if not q:
        return []
    seeds: list[str] = []
    for part in _ENTITY_SPLIT.split(q):
        part = part.strip("？?。.")
        if 2 <= len(part) <= 32:
            seeds.extend(list_entities_matching(part, limit=3))
    if not seeds and len(q) <= 24:
        seeds.extend(list_entities_matching(q[:12], limit=5))
    seen: set[str] = set()
    out: list[str] = []
    for s in seeds:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out[:8]


def graph_expand_retrieval(
    question: str,
    user_department: str,
    *,
    max_hops: int = 2,
    limit: int = 20,
) -> list[dict[str, Any]]:
    seeds = seed_entities_from_question(question)
    if not seeds:
        return []
    edges = expand_from_seeds(
        seeds,
        department=user_department,
        max_hops=max_hops,
        limit=limit,
    )
    parent_ids = []
    seen: set[str] = set()
    for e in edges:
        pid = str(e.get("parent_id") or "")
        if pid and pid not in seen:
            seen.add(pid)
            parent_ids.append(pid)
    if not parent_ids:
        return []
    fetched = fetch_parents_by_ids(parent_ids)
    parents: list[dict[str, Any]] = []
    for pid in parent_ids:
        row = fetched.get(pid)
        if not row:
            continue
        parents.append(
            {
                "parent_id": pid,
                "text": str(row.get("text") or ""),
                "department": str(row.get("department") or user_department),
                "source": str(row.get("source") or ""),
                "permission_label": str(row.get("permission_label") or ""),
                "tags": row.get("tags") or [],
                "hybrid_score": 0.75,
                "graph_score": 1.0,
            }
        )
    return parents


def rrf_fuse_parents(
    hybrid_parents: list[dict[str, Any]],
    graph_parents: list[dict[str, Any]],
    *,
    k: int = 60,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion of hybrid and graph candidate lists."""
    scores: dict[str, float] = {}
    rows: dict[str, dict[str, Any]] = {}

    def _add_ranked(items: list[dict[str, Any]], weight: float = 1.0) -> None:
        for rank, row in enumerate(items):
            pid = str(row.get("parent_id") or "")
            if not pid:
                continue
            scores[pid] = scores.get(pid, 0.0) + weight / (k + rank + 1)
            rows.setdefault(pid, row)

    _add_ranked(hybrid_parents, 1.0)
    _add_ranked(graph_parents, 1.2)

    ordered = sorted(scores.keys(), key=lambda pid: -scores[pid])
    out: list[dict[str, Any]] = []
    for pid in ordered[:top_k]:
        row = dict(rows[pid])
        row["hybrid_score"] = max(float(row.get("hybrid_score") or 0), scores[pid])
        row["rrf_score"] = scores[pid]
        out.append(row)
    return out
