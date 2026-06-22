"""Analyze retrieval-miss feedback and rank query alias candidates (Phase 3)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from retrieval.query_aliases_store import alias_patch_from_question
from retrieval.query_normalize import normalize_query


def _question_key(text: str) -> str:
    return normalize_query((text or "").strip()) or (text or "").strip()


def propose_alias_candidates(
    questions: list[str],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Rank alias patches inferred from miss queries (same canonical merged)."""
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for raw_q in questions:
        q = (raw_q or "").strip()
        if not q:
            continue
        patch = alias_patch_from_question(q)
        if not patch:
            continue
        canon = str(patch.get("canonical") or "").strip()
        if not canon:
            continue
        for alias in patch.get("aliases") or []:
            alias_s = str(alias).strip()
            if not alias_s or alias_s == canon:
                continue
            key = (canon, alias_s)
            row = buckets.setdefault(
                key,
                {
                    "canonical": canon,
                    "alias": alias_s,
                    "count": 0,
                    "sample_questions": [],
                },
            )
            row["count"] += 1
            if q not in row["sample_questions"]:
                row["sample_questions"].append(q)
    ranked = sorted(buckets.values(), key=lambda r: (-int(r["count"]), r["canonical"], r["alias"]))
    for row in ranked:
        row["sample_questions"] = row["sample_questions"][:5]
        row["confidence"] = round(min(0.95, 0.5 + 0.1 * row["count"]), 3)
    return ranked[: max(1, limit)]


def cluster_miss_questions(
    questions: list[str],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Group similar miss queries by normalized form."""
    groups: dict[str, dict[str, Any]] = {}
    for raw_q in questions:
        q = (raw_q or "").strip()
        if not q:
            continue
        key = _question_key(q)
        row = groups.setdefault(key, {"normalized": key, "count": 0, "samples": []})
        row["count"] += 1
        if q not in row["samples"]:
            row["samples"].append(q)
    ranked = sorted(groups.values(), key=lambda r: (-int(r["count"]), r["normalized"]))
    for row in ranked:
        row["samples"] = row["samples"][:5]
    return ranked[: max(1, limit)]


def analyze_retrieval_misses(
    feedback_rows: list[dict[str, Any]],
    *,
    alias_limit: int = 20,
    cluster_limit: int = 20,
) -> dict[str, Any]:
    """Build alias proposals + question clusters from feedback rows."""
    questions: list[str] = []
    for row in feedback_rows:
        if int(row.get("rating") or 0) > 0:
            continue
        issue = str(row.get("issue_type") or "").strip()
        if issue and issue not in ("retrieval_miss", "prompt", "unknown", ""):
            continue
        q = str(row.get("question") or "").strip()
        if q:
            questions.append(q)
    return {
        "question_count": len(questions),
        "alias_candidates": propose_alias_candidates(questions, limit=alias_limit),
        "question_clusters": cluster_miss_questions(questions, limit=cluster_limit),
    }
