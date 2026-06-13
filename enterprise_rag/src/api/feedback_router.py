"""User feedback + admin listing + triage (Sprint A/B)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from api.schemas import (
    ConfigRevisionListResponse,
    ConfigRevisionPublic,
    EvalReportListResponse,
    EvalReportPublic,
    FeedbackActionResult,
    FeedbackEvaluateRequest,
    FeedbackEvaluateResponse,
    FeedbackListResponse,
    FeedbackPublic,
    FeedbackRequest,
    FeedbackStatusResponse,
    FeedbackSuggestedAction,
    FeedbackTriageRequest,
    FeedbackTriageResponse,
)
from feedback_loop.config_revisions import diff_revision, get_revision, list_revisions, rollback_revision
from feedback_loop.eval_store import export_reports_json, get_eval_report, list_eval_reports
from feedback_loop.evaluate import extract_revision_id, run_golden_evaluation, run_golden_evaluation_safe
from feedback_loop.queue import InvalidTransitionError, approve_and_apply, reject_feedback
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


def _action_results(raw: list | None) -> list[FeedbackActionResult]:
    out: list[FeedbackActionResult] = []
    for r in raw or []:
        if not isinstance(r, dict):
            continue
        out.append(
            FeedbackActionResult(
                action=str(r.get("action") or ""),
                ok=bool(r.get("ok")),
                skipped=r.get("skipped"),
                reason=r.get("reason"),
                error=r.get("error"),
                revision_id=r.get("revision_id"),
                proposal_id=r.get("proposal_id"),
                golden_path=r.get("golden_path"),
            )
        )
    return out


def _to_status(row: dict) -> FeedbackStatusResponse:
    pub = _to_public(row)
    return FeedbackStatusResponse(
        id=pub.id,
        status=pub.status,
        issue_type=pub.issue_type,
        severity=pub.severity,
        triage_summary=pub.triage_summary,
        action_results=_action_results(row.get("action_results")),
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
def admin_approve_feedback(feedback_id: str, background_tasks: BackgroundTasks):
    """采纳建议并执行 Actuator 白名单动作；成功后异步跑 golden 评测。"""
    try:
        row = approve_and_apply(feedback_id)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except KeyError:
        raise HTTPException(status_code=404, detail="Feedback not found") from None
    if str(row.get("status") or "") == "applied":
        revision_id = extract_revision_id(row.get("action_results"))
        background_tasks.add_task(
            run_golden_evaluation_safe,
            feedback_id=feedback_id,
            revision_id=revision_id,
        )
    return _to_status(row)


@router.post("/admin/feedback/evaluate", response_model=FeedbackEvaluateResponse)
def admin_run_feedback_evaluate(body: FeedbackEvaluateRequest | None = None):
    """手动触发 golden 评测（RAGAS 或 naive 回退），对比上一份报告 delta。"""
    req = body or FeedbackEvaluateRequest()
    out = run_golden_evaluation(
        feedback_id=req.feedback_id,
        revision_id=req.revision_id,
        mark_feedback_evaluated=bool(req.feedback_id),
    )
    if not out.get("ok"):
        return FeedbackEvaluateResponse(ok=False, error=str(out.get("error") or "evaluate failed"))
    return FeedbackEvaluateResponse(
        ok=True,
        report_id=out.get("report_id"),
        feedback_id=out.get("feedback_id"),
        revision_id=out.get("revision_id"),
        golden_rows=int(out.get("golden_rows") or 0),
        mode=str(out.get("mode") or ""),
        metrics=dict(out.get("metrics") or {}),
        delta=dict(out.get("delta") or {}),
        created_at=out.get("created_at"),
    )


@router.get("/admin/feedback/eval-reports", response_model=EvalReportListResponse)
def admin_list_eval_reports(
    feedback_id: str | None = Query(default=None, max_length=64),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    rows, total = list_eval_reports(feedback_id=feedback_id, offset=offset, limit=limit)
    items = [
        EvalReportPublic(
            id=str(r["id"]),
            created_at=str(r.get("created_at") or ""),
            feedback_id=r.get("feedback_id"),
            revision_id=r.get("revision_id"),
            golden_rows=int(r.get("golden_rows") or 0),
            mode=str(r.get("mode") or "fallback_naive"),
            metrics=dict(r.get("metrics") or {}),
            baseline_metrics=dict(r.get("baseline_metrics") or {}),
            delta=dict(r.get("delta") or {}),
        )
        for r in rows
    ]
    return EvalReportListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/admin/feedback/eval-reports/{report_id}", response_model=EvalReportPublic)
def admin_get_eval_report(report_id: str):
    row = get_eval_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return EvalReportPublic(
        id=str(row["id"]),
        created_at=str(row.get("created_at") or ""),
        feedback_id=row.get("feedback_id"),
        revision_id=row.get("revision_id"),
        golden_rows=int(row.get("golden_rows") or 0),
        mode=str(row.get("mode") or "fallback_naive"),
        metrics=dict(row.get("metrics") or {}),
        baseline_metrics=dict(row.get("baseline_metrics") or {}),
        delta=dict(row.get("delta") or {}),
    )


@router.post("/admin/feedback/eval-reports/export")
def admin_export_eval_reports():
    reports = export_reports_json()
    return {"ok": True, "exported": len(reports), "items": reports}


@router.get("/admin/feedback/config-revisions", response_model=ConfigRevisionListResponse)
def admin_list_config_revisions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    rows, total = list_revisions(offset=offset, limit=limit)
    items = [
        ConfigRevisionPublic(
            id=str(r["id"]),
            created_at=str(r.get("created_at") or ""),
            feedback_id=str(r.get("feedback_id") or ""),
            tenant_id=str(r.get("tenant_id") or "internal"),
            action=str(r.get("action") or ""),
            patch=dict(r.get("patch") or {}),
            rolled_back=bool(r.get("rolled_back")),
            rolled_back_at=r.get("rolled_back_at"),
            diff=diff_revision(r),
        )
        for r in rows
    ]
    return ConfigRevisionListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/admin/feedback/config-revisions/{revision_id}/rollback")
def admin_rollback_config_revision(revision_id: str):
    try:
        row = rollback_revision(revision_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Revision not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    rev = get_revision(revision_id)
    assert rev is not None
    return {
        "ok": True,
        "id": revision_id,
        "rolled_back": bool(row.get("rolled_back")),
        "diff": diff_revision(rev),
    }


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
