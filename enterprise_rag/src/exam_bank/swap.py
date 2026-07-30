"""Swap / replace a question with same-pool alternatives (assemble fine-tune)."""

from __future__ import annotations

from typing import Any

from exam_bank import store
from exam_bank.subject_catalog import normalize_qtype


def find_swap_candidates(
    *,
    collection_id: str,
    question_id: str,
    exclude_ids: list[str] | None = None,
    limit: int = 5,
    soft_fallback: bool = True,
) -> dict[str, Any]:
    current = store.get_question(question_id)
    if not current or current.get("collection_id") != collection_id:
        return {"ok": False, "error": "question_not_found", "candidates": []}

    excluded = {str(x) for x in (exclude_ids or []) if str(x).strip()}
    excluded.add(str(question_id))
    qt = normalize_qtype(str(current.get("qtype") or "other"))
    tags = {str(t).strip() for t in (current.get("knowledge_tags") or []) if str(t).strip()}
    diff = int(current.get("difficulty") or 3)

    pool, _ = store.list_questions(
        collection_id=collection_id,
        status="published",
        limit=500,
        offset=0,
    )
    same_type = [
        q
        for q in pool
        if str(q.get("id")) not in excluded
        and normalize_qtype(str(q.get("qtype") or "other")) == qt
    ]

    def _score(q: dict[str, Any]) -> tuple[int, int, str]:
        qtags = {str(t).strip() for t in (q.get("knowledge_tags") or []) if str(t).strip()}
        overlap = len(tags & qtags) if tags else 0
        d = abs(int(q.get("difficulty") or 3) - diff)
        return (-overlap, d, str(q.get("id") or ""))

    tagged = [q for q in same_type if tags and tags.intersection(q.get("knowledge_tags") or [])]
    fallback_applied = False
    chosen = tagged
    if not chosen:
        if soft_fallback:
            chosen = same_type
            fallback_applied = True
        else:
            return {
                "ok": True,
                "candidates": [],
                "fallback_applied": False,
                "fallback_notes": ["无同知识点备选"],
            }

    chosen = sorted(chosen, key=_score)[: max(1, min(20, int(limit or 5)))]
    notes: list[str] = []
    if fallback_applied:
        notes.append("已放宽：同题型备选（无同知识点）")
    return {
        "ok": True,
        "question_id": question_id,
        "candidates": chosen,
        "fallback_applied": fallback_applied,
        "fallback_notes": notes,
    }
