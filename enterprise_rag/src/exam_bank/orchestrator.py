"""Exam-bank domain orchestrator (11.txt 阶段二入口).

Not a parallel Agent runtime — call existing services only.
Complex multi-step LLM flows should register as DeerFlow tools later
(see docs/deerflow-integration.md; deferred items in docs/exam-bank-issues.md).
"""

from __future__ import annotations

from typing import Any

from exam_bank import assemble, store
from exam_bank.lesson import lesson_from_paper
from exam_bank.swap import find_swap_candidates
from exam_bank.types import DEFAULT_TENANT


def auto_generate_paper(
    *,
    collection_id: str,
    title: str,
    spec: dict[str, Any] | None = None,
    include_answers: bool = True,
    tenant_id: str = DEFAULT_TENANT,
    soft_fallback: bool | None = None,
) -> dict[str, Any]:
    """Constraint assemble with optional soft fallback (智能兜底)."""
    col = store.get_collection(collection_id)
    if not col:
        return {"ok": False, "error": "collection_not_found"}
    spec_in = dict(spec or {})
    if soft_fallback is not None:
        spec_in["soft_fallback"] = bool(soft_fallback)
    elif "soft_fallback" not in spec_in:
        spec_in["soft_fallback"] = True
    # Region locked to collection
    region = str(col.get("region") or "").strip()
    if region:
        spec_in["regions_any"] = [region]
    return assemble.assemble_paper(
        collection_id=collection_id,
        title=title,
        spec=spec_in,
        include_answers=include_answers,
        tenant_id=tenant_id,
    )


def generate_lesson(
    *,
    paper_id: str,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Lesson plan from assembled paper. Rules-first; LLM via DeerFlow later."""
    _ = use_llm  # reserved for async DeerFlow tool path
    return lesson_from_paper(paper_id)


def swap_question(
    *,
    collection_id: str,
    question_id: str,
    exclude_ids: list[str] | None = None,
    limit: int = 5,
    soft_fallback: bool = True,
) -> dict[str, Any]:
    return find_swap_candidates(
        collection_id=collection_id,
        question_id=question_id,
        exclude_ids=exclude_ids,
        limit=limit,
        soft_fallback=soft_fallback,
    )
