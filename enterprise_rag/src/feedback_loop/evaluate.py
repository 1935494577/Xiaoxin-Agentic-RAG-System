"""Golden evaluation + delta vs previous report (Sprint D)."""

from __future__ import annotations

import logging
from typing import Any

from evaluation.golden_eval import load_golden_rows, run_golden_metrics
from feedback_loop.eval_store import append_eval_report, get_latest_report
from feedback_loop.queue import InvalidTransitionError, transition_status

_log = logging.getLogger(__name__)

_NUMERIC_SKIP = frozenset({"rows", "mode", "ragas_error", "ragas_debug"})


def compute_metric_delta(
    current: dict[str, Any],
    baseline_report: dict[str, Any] | None,
) -> dict[str, float]:
    if not baseline_report:
        return {}
    baseline = baseline_report.get("metrics")
    if not isinstance(baseline, dict):
        return {}
    delta: dict[str, float] = {}
    for key, cur_val in current.items():
        if key in _NUMERIC_SKIP:
            continue
        base_val = baseline.get(key)
        try:
            cur_f = float(cur_val)  # type: ignore[arg-type]
            base_f = float(base_val)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        delta[key] = round(cur_f - base_f, 6)
    return delta


def run_golden_evaluation(
    *,
    feedback_id: str | None = None,
    revision_id: str | None = None,
    mark_feedback_evaluated: bool = True,
) -> dict[str, Any]:
    rows = load_golden_rows()
    n = len(rows.get("question") or [])
    if n == 0:
        return {"ok": False, "error": "golden.jsonl is empty or missing"}

    metrics = run_golden_metrics(rows)
    baseline_report = get_latest_report(
        feedback_id=None if revision_id else feedback_id,
    )
    # revision 对比：基线取全站上一份报告（含 revision 或不含）
    if revision_id and not baseline_report:
        baseline_report = get_latest_report()
    delta = compute_metric_delta(metrics, baseline_report)
    mode = str(metrics.get("mode") or "unknown")

    report = append_eval_report(
        metrics=metrics,
        golden_rows=n,
        feedback_id=feedback_id,
        revision_id=revision_id,
        baseline_metrics=dict((baseline_report or {}).get("metrics") or {}),
        delta=delta,
        mode=mode,
    )

    if mark_feedback_evaluated and feedback_id:
        try:
            transition_status(feedback_id, "evaluated")
        except (InvalidTransitionError, KeyError, ValueError):
            _log.debug("skip evaluated transition for %s", feedback_id, exc_info=True)

    return {
        "ok": True,
        "report_id": report["id"],
        "feedback_id": feedback_id,
        "revision_id": revision_id,
        "golden_rows": n,
        "mode": mode,
        "metrics": metrics,
        "delta": delta,
        "created_at": report["created_at"],
    }


def run_golden_evaluation_safe(
    *,
    feedback_id: str | None = None,
    revision_id: str | None = None,
) -> None:
    """Background-safe wrapper."""
    try:
        run_golden_evaluation(
            feedback_id=feedback_id,
            revision_id=revision_id,
            mark_feedback_evaluated=bool(feedback_id),
        )
    except Exception:
        _log.exception(
            "golden evaluation failed feedback_id=%s revision_id=%s",
            feedback_id,
            revision_id,
        )


def extract_revision_id(action_results: list[dict[str, Any]] | None) -> str | None:
    for item in action_results or []:
        if not isinstance(item, dict):
            continue
        rid = item.get("revision_id")
        if rid:
            return str(rid)
    return None
