"""Chat-facing exam paper payload + objective attempt grading."""

from __future__ import annotations

import re
from typing import Any

from exam_bank import store
from exam_bank.paper_layout import group_questions_by_qtype, section_heading
from exam_bank.subject_catalog import qtype_label

_OBJECTIVE = frozenset({"choice", "multi", "fill"})
_LETTER_RE = re.compile(r"^\s*([A-Da-d])\b")


def normalize_objective_answer(raw: str, qtype: str) -> str:
    s = (raw or "").strip()
    qt = (qtype or "").strip().lower()
    if qt in ("choice", "multi"):
        m = _LETTER_RE.match(s)
        if m:
            return m.group(1).upper()
        if len(s) == 1 and s.isalpha():
            return s.upper()
        return s.upper()
    return s


def _public_item(q: dict[str, Any], *, include_answers: bool) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": q["id"],
        "no": str(q.get("question_no") or "").strip(),
        "qtype": q.get("qtype") or "other",
        "qtype_label": qtype_label(str(q.get("qtype") or "other")),
        "score": 5 if (q.get("qtype") or "") in ("choice", "multi") else 0,
        "stem": q.get("stem") or "",
        "options": list(q.get("options") or []),
        "media_ingest_id": str(q.get("media_ingest_id") or "").strip(),
    }
    if include_answers:
        item["answer"] = q.get("answer") or ""
        item["analysis"] = q.get("analysis") or ""
    return item


def build_chat_paper(
    source_paper_id: str,
    *,
    include_answers: bool = False,
) -> dict[str, Any]:
    sp = store.get_source_paper(source_paper_id)
    if not sp:
        return {"ok": False, "error": "source_paper_not_found", "message": "试卷不存在"}

    questions: list[dict[str, Any]] = []
    for qid in sp.get("question_ids") or []:
        q = store.get_question(str(qid))
        if q:
            questions.append(q)
    if not questions:
        # fallback: questions linked by source_paper_id
        items, _ = store.list_questions(
            collection_id=sp["collection_id"],
            status=None,
            limit=500,
            offset=0,
        )
        questions = [q for q in items if str(q.get("source_paper_id") or "") == sp["id"]]
        questions.sort(key=lambda x: str(x.get("question_no") or ""))

    order, by_type = group_questions_by_qtype(questions)
    sections: list[dict[str, Any]] = []
    for si, qt in enumerate(order):
        group = by_type.get(qt) or []
        if not group:
            continue
        sections.append(
            {
                "heading": section_heading(si, qt, len(group)),
                "qtype": qt,
                "items": [_public_item(q, include_answers=include_answers) for q in group],
            }
        )

    total_score = sum(int(it.get("score") or 0) for sec in sections for it in sec["items"])
    return {
        "ok": True,
        "type": "exam_paper",
        "paper_id": sp["id"],
        "source_paper_id": sp["id"],
        "collection_id": sp["collection_id"],
        "title": sp.get("title") or "未命名试卷",
        "source_filename": sp.get("source_filename") or "",
        "media_ingest_id": sp.get("media_ingest_id") or "",
        "meta": {
            "total_score": total_score or len(questions) * 5,
            "question_count": len(questions),
            "duration_min": 120,
        },
        "sections": sections,
        "mode": "preview" if not include_answers else "review",
    }


def start_attempt(source_paper_id: str, *, user_id: str = "") -> dict[str, Any]:
    paper = build_chat_paper(source_paper_id, include_answers=False)
    if not paper.get("ok"):
        return paper
    row = store.create_exam_attempt(
        source_paper_id=source_paper_id,
        user_id=user_id,
        paper_snapshot=paper,
    )
    return {
        "ok": True,
        "attempt_id": row["id"],
        "status": row["status"],
        "paper": paper,
        "started_at": row["created_at"],
    }


def grade_attempt(
    *,
    paper: dict[str, Any],
    answers: dict[str, str],
) -> dict[str, Any]:
    """Grade objective items; subjective marked unscored."""
    results: list[dict[str, Any]] = []
    correct_count = 0
    graded_count = 0
    # need ground truth from DB
    for sec in paper.get("sections") or []:
        for it in sec.get("items") or []:
            qid = str(it.get("id") or "")
            q = store.get_question(qid) if qid else None
            if not q:
                continue
            qt = str(q.get("qtype") or "")
            user_ans = str((answers or {}).get(qid) or "").strip()
            key = str(q.get("answer") or "").strip()
            entry: dict[str, Any] = {
                "question_id": qid,
                "qtype": qt,
                "user_answer": user_ans,
                "answer": key,
                "analysis": q.get("analysis") or "",
                "correct": None,
                "scored": False,
            }
            if qt in _OBJECTIVE and key:
                graded_count += 1
                entry["scored"] = True
                u_n = normalize_objective_answer(user_ans, qt)
                k_n = normalize_objective_answer(key, qt)
                ok = u_n == k_n
                entry["correct"] = ok
                if ok:
                    correct_count += 1
            results.append(entry)
    score = correct_count
    max_score = graded_count
    return {
        "correct_count": correct_count,
        "graded_count": graded_count,
        "score": score,
        "max_score": max_score,
        "results": results,
    }


def submit_attempt(attempt_id: str, *, answers: dict[str, str]) -> dict[str, Any]:
    row = store.get_exam_attempt(attempt_id)
    if not row:
        return {"ok": False, "error": "attempt_not_found", "message": "答题会话不存在"}
    if row.get("status") == "submitted":
        return {
            "ok": True,
            "attempt_id": attempt_id,
            "status": "submitted",
            "correct_count": row.get("correct_count"),
            "graded_count": row.get("graded_count"),
            "score": row.get("score"),
            "max_score": row.get("max_score"),
            "results": row.get("results") or [],
            "message": "已交卷",
        }
    paper = row.get("paper_snapshot") or build_chat_paper(
        row["source_paper_id"], include_answers=False
    )
    graded = grade_attempt(paper=paper, answers=answers)
    updated = store.finish_exam_attempt(
        attempt_id,
        answers=answers,
        results=graded["results"],
        score=int(graded["score"]),
        max_score=int(graded["max_score"]),
        correct_count=int(graded["correct_count"]),
        graded_count=int(graded["graded_count"]),
    )
    return {
        "ok": True,
        "attempt_id": attempt_id,
        "status": updated["status"],
        "correct_count": updated["correct_count"],
        "graded_count": updated["graded_count"],
        "score": updated["score"],
        "max_score": updated["max_score"],
        "results": updated.get("results") or [],
    }
