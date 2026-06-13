"""Feedback actuator + config revisions (Sprint C)."""

from __future__ import annotations

import json

import pytest

from config import settings
from feedback_loop.actuator import (
    BLOCKED_ACTIONS,
    execute_feedback_actions,
    execute_single_action,
)
from feedback_loop.config_revisions import (
    list_revisions,
    rollback_revision,
)
from feedback_loop.queue import approve_and_apply
from feedback_loop.store import (
    enrich_feedback,
    get_feedback,
    init_feedback_db,
    insert_feedback,
    save_triage_result,
)


@pytest.fixture()
def actuator_env(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    ui_path = tmp_path / "ui_config.json"
    ui_path.write_text(
        json.dumps({"kb_min_score": 0.55, "kb_min_rerank_score": 0.0}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "golden_jsonl_path", eval_dir / "golden.jsonl")
    monkeypatch.setattr(settings, "config_revisions_path", tmp_path / "config_revisions.jsonl")
    monkeypatch.setattr(settings, "ingest_proposals_path", tmp_path / "ingest_proposals.jsonl")
    monkeypatch.setattr(settings, "retrieval_tuning_path", tmp_path / "retrieval_tuning.json")
    monkeypatch.setattr(settings, "ui_config_path", ui_path)
    init_feedback_db()
    return tmp_path


def _triaged_row(
    *,
    rating: int = 0,
    question: str = "测试问题",
    answer: str = "测试答案",
    correction: str = "",
    actions: list[dict] | None = None,
) -> str:
    fid = insert_feedback(
        user_id="u1",
        rating=rating,
        question=question,
        answer_preview=answer,
        correction=correction or None,
    )
    enrich_feedback(
        fid,
        context_count=2,
        sources=["doc-a.pdf"],
        trace_snapshot={"spans": []},
    )
    save_triage_result(
        fid,
        issue_type="hallucination",
        severity="medium",
        summary="test",
        human_review_required=True,
        suggested_actions=actions
        or [{"action": "add_to_golden", "confidence": 0.9, "detail": "加入评测集"}],
    )
    row = get_feedback(fid)
    assert row is not None
    return fid


def test_blocked_actions_registry():
    assert "delete_index" in BLOCKED_ACTIONS


def test_add_to_golden_writes_jsonl(actuator_env, tmp_path):
    fid = _triaged_row()
    row = get_feedback(fid)
    assert row is not None
    results = execute_single_action(row, {"action": "add_to_golden", "confidence": 0.9})
    assert results["ok"] is True
    golden = settings.golden_jsonl_path
    assert golden.is_file()
    line = json.loads(golden.read_text(encoding="utf-8").strip())
    assert line["question"] == "测试问题"
    assert line["ground_truth"] == "测试答案" or line.get("answer")


def test_propose_reingest_appends_proposal(actuator_env):
    fid = _triaged_row(
        actions=[{"action": "propose_reingest", "confidence": 0.6, "detail": "重入库"}]
    )
    row = get_feedback(fid)
    assert row is not None
    results = execute_single_action(row, row["suggested_actions"][0])
    assert results["ok"] is True
    proposals = settings.ingest_proposals_path.read_text(encoding="utf-8").strip()
    obj = json.loads(proposals)
    assert obj["feedback_id"] == fid
    assert obj["sources"] == ["doc-a.pdf"]


def test_apply_config_patch_ui_and_revision(actuator_env):
    fid = _triaged_row(
        actions=[
            {
                "action": "apply_config_patch",
                "confidence": 0.5,
                "patch": {"ui_config": {"kb_min_score": 0.45}},
            }
        ]
    )
    row = get_feedback(fid)
    assert row is not None
    results = execute_single_action(row, row["suggested_actions"][0])
    assert results["ok"] is True
    ui = json.loads(settings.ui_config_path.read_text(encoding="utf-8"))
    assert ui["kb_min_score"] == 0.45
    revs, total = list_revisions(limit=10)
    assert total == 1
    assert revs[0]["action"] == "apply_config_patch"


def test_config_revision_rollback(actuator_env):
    fid = _triaged_row(
        actions=[
            {
                "action": "apply_config_patch",
                "confidence": 0.5,
                "patch": {"ui_config": {"kb_min_score": 0.4}},
            }
        ]
    )
    row = get_feedback(fid)
    assert row is not None
    execute_single_action(row, row["suggested_actions"][0])
    rev_id = list_revisions(limit=1)[0][0]["id"]
    rolled = rollback_revision(rev_id)
    assert rolled["rolled_back"] is True
    ui = json.loads(settings.ui_config_path.read_text(encoding="utf-8"))
    assert ui["kb_min_score"] == 0.55


def test_approve_and_apply_transitions_to_applied(actuator_env):
    fid = _triaged_row()
    out = approve_and_apply(fid)
    assert out["status"] == "applied"
    assert out.get("action_results")
    assert any(r.get("ok") for r in out["action_results"])


def test_execute_skips_low_confidence_add_to_golden_without_approval(actuator_env):
    fid = _triaged_row(
        actions=[{"action": "add_to_golden", "confidence": 0.5, "detail": "低置信"}]
    )
    row = get_feedback(fid)
    assert row is not None
    results = execute_feedback_actions(row, manual=False)
    assert results[0]["ok"] is False
    assert not settings.golden_jsonl_path.exists()


def test_execute_runs_all_on_manual_approve(actuator_env):
    fid = _triaged_row(
        actions=[{"action": "add_to_golden", "confidence": 0.5, "detail": "低置信"}]
    )
    row = get_feedback(fid)
    assert row is not None
    results = execute_feedback_actions(row, manual=True)
    assert results[0]["ok"] is True
