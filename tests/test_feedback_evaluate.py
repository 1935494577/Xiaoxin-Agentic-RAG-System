"""Feedback evaluate loop (Sprint D)."""

from __future__ import annotations

import json

import pytest

from config import settings
from feedback_loop.evaluate import compute_metric_delta, run_golden_evaluation
from feedback_loop.eval_store import append_eval_report, get_latest_report, list_eval_reports
from feedback_loop.queue import approve_and_apply
from feedback_loop.store import enrich_feedback, init_feedback_db, insert_feedback, save_triage_result


@pytest.fixture()
def eval_env(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    golden = eval_dir / "golden.jsonl"
    golden.write_text(
        json.dumps(
            {
                "question": "Q",
                "answer": "LangGraph orchestrates steps.",
                "contexts": ["LangGraph orchestrates rewrite, retrieve, rerank, and generate steps."],
                "ground_truth": "LangGraph",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "golden_jsonl_path", golden)
    monkeypatch.setattr(settings, "eval_reports_path", eval_dir / "eval_reports.jsonl")
    monkeypatch.setattr(settings, "openai_api_key", "")
    init_feedback_db()
    return tmp_path


def test_run_golden_evaluation_naive_fallback(eval_env):
    report = run_golden_evaluation()
    assert report["ok"] is True
    assert report["metrics"]["mode"] == "fallback_naive"
    assert report["golden_rows"] == 1
    assert "naive_context_answer_overlap_rate" in report["metrics"]


def test_metric_delta_vs_previous(eval_env):
    append_eval_report(
        metrics={"naive_context_answer_overlap_rate": 0.5, "rows": 2.0, "mode": "fallback_naive"},
        golden_rows=2,
    )
    delta = compute_metric_delta(
        {"naive_context_answer_overlap_rate": 0.75, "rows": 3.0},
        get_latest_report(),
    )
    assert delta["naive_context_answer_overlap_rate"] == pytest.approx(0.25)


def test_approve_triggers_evaluated_status(eval_env):
    fid = insert_feedback(user_id="u1", rating=0, question="Q", correction="fix")
    enrich_feedback(fid, context_count=1, sources=["a.pdf"])
    save_triage_result(
        fid,
        issue_type="hallucination",
        severity="medium",
        summary="x",
        human_review_required=True,
        suggested_actions=[{"action": "add_to_golden", "confidence": 0.9}],
    )
    out = approve_and_apply(fid)
    assert out["status"] == "applied"
    report = run_golden_evaluation(feedback_id=fid)
    assert report["ok"] is True
    assert report["feedback_id"] == fid
    from feedback_loop.store import get_feedback

    row = get_feedback(fid)
    assert row["status"] == "evaluated"


def test_list_eval_reports(eval_env):
    run_golden_evaluation()
    items, total = list_eval_reports(limit=10)
    assert total >= 1
    assert items[0]["id"]
