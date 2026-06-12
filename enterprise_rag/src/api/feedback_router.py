"""User feedback + admin listing + triage (Sprint A/B)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api.schemas import (
    FeedbackListResponse,
    FeedbackPublic,
    FeedbackRequest,
    FeedbackStatusResponse,
    FeedbackSuggestedAction,
    FeedbackTriageRequest,
    FeedbackTriageResponse,
)
from feedback_loop.queue import InvalidTransitionError, approve_feedback, reject_feedback
from feedback_loop.service import enrich_feedback_from_trace, export_all_feedback_jsonl, submit_feedback_record
from feedback_loop.store import get_feedback, list_feedback
from feedback_loop.trace_loader import load_trace_by_id
from feedback_loop.triage import run_triage_batch

router = APIRouter(tags=["feedback"])


def _to_public(row: dict) -> FeedbackPublic:
    actions = [
        FeedbackSuggestedAction(
            action=str(a.get("action") or ""),
            confidence=float(a["confidence"]) if a.get("confidence") is not None else None,
            detail=str(a.get("detail") or "") or None,
        )
        for a in (row.get("suggested_actions") or [])
        if isinstance(a, dict)
    ]
    return FeedbackPublic(
        id=str(row["id"]),
        tenant_id=str(row.get("tenant_id") or "internal"),
        user_id=str(row["user_id"]),
        rating=int(row["rating"]),
        trace_id=row.get("trace_id"),
        session_id=row.get("session_id"),
        message_id=row.get("message_id"),
        question=row.get("question"),
        answer_preview=row.get("answer_preview"),
        answer_mode=row.get("answer_mode"),
        correction=row.get("correction"),
        context_count=row.get("context_count"),
        sources=list(row.get("sources") or []),
        status=str(row.get("status") or "pending"),
        issue_type=row.get("issue_type"),
        severity=row.get("severity"),
        human_review_required=row.get("human_review_required"),
        triage_summary=row.get("triage_summary"),
        suggested_actions=actions,
        created_at=str(row["created_at"]),
        updated_at=row.get("updated_at"),
    )


def _to_status(row: dict) -> FeedbackStatusResponse:
    pub = _to_public(row)
    return FeedbackStatusResponse(
        id=pub.id,
        status=pub.status,
        issue_type=pub.issue_type,
        severity=pub.severity,
        triage_summary=pub.triage_summary,
    )


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, background_tasks: BackgroundTasks):
    """用户反馈：同步写入 SQLite，异步补全 trace 快照并导出 JSONL。"""
    fid = submit_feedback_record(
        user_id=req.user_id,
        rating=req.rating,
        trace_id=req.trace_id,
        message_id=req.message_id,
        session_id=req.session_id,
        question=req.question,
        answer_preview=req.answer_preview,
        answer_mode=req.answer_mode,
        correction=req.correction,
    )
    background_tasks.add_task(enrich_feedback_from_trace, fid)
    return {"ok": True, "id": fid}


@router.get("/admin/feedback", response_model=FeedbackListResponse)
def admin_list_feedback(
    user_id: str | None = Query(default=None, max_length=128),
    trace_id: str | None = Query(default=None, max_length=128),
    rating: int | None = Query(default=None, ge=-1, le=1),
    status: str | None = Query(default=None, max_length=32),
    sort: str = Query(default="created_desc", pattern="^(created_desc|severity_desc|severity_asc)$"),
    since_days: int = Query(default=7, ge=1, le=365),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
):
    rows, total = list_feedback(
        user_id=user_id,
        trace_id=trace_id,
        rating=rating,
        status=status,
        sort=sort,
        since_days=since_days,
        offset=offset,
        limit=limit,
    )
    return FeedbackListResponse(
        items=[_to_public(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/admin/feedback/triage", response_model=FeedbackTriageResponse)
def admin_triage_feedback(body: FeedbackTriageRequest):
    """批量 Triage（冷路径，不在 /chat 热路径）。"""
    out = run_triage_batch(limit=body.limit, use_llm=body.use_llm, rating=body.rating)
    return FeedbackTriageResponse(**out)


@router.post("/admin/feedback/{feedback_id}/approve", response_model=FeedbackStatusResponse)
def admin_approve_feedback(feedback_id: str):
    try:
        row = approve_feedback(feedback_id)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except KeyError:
        raise HTTPException(status_code=404, detail="Feedback not found") from None
    return _to_status(row)


@router.post("/admin/feedback/{feedback_id}/reject", response_model=FeedbackStatusResponse)
def admin_reject_feedback(feedback_id: str):
    try:
        row = reject_feedback(feedback_id)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except KeyError:
        raise HTTPException(status_code=404, detail="Feedback not found") from None
    return _to_status(row)


@router.get("/admin/feedback/traces/{trace_id}")
def admin_get_trace(trace_id: str):
    trace = load_trace_by_id(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@router.get("/admin/feedback/{feedback_id}", response_model=FeedbackPublic)
def admin_get_feedback(feedback_id: str):
    row = get_feedback(feedback_id)
    if not row:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return _to_public(row)


@router.post("/admin/feedback/export-jsonl")
def admin_export_feedback_jsonl():
    count = export_all_feedback_jsonl()
    return {"ok": True, "exported": count}
