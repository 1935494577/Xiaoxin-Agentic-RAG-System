"""Feedback API Sprint C — approve runs actuator."""

import json

import pytest
from fastapi.testclient import TestClient

from config import settings
from feedback_loop.store import enrich_feedback, insert_feedback, save_triage_result


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "chat_sessions.db"
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    ui_path = tmp_path / "ui_config.json"
    ui_path.write_text(json.dumps({"kb_min_score": 0.55}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(settings, "chat_sessions_db_path", db)
    monkeypatch.setattr(settings, "golden_jsonl_path", eval_dir / "golden.jsonl")
    monkeypatch.setattr(settings, "config_revisions_path", tmp_path / "config_revisions.jsonl")
    monkeypatch.setattr(settings, "ingest_proposals_path", tmp_path / "ingest_proposals.jsonl")
    monkeypatch.setattr(settings, "retrieval_tuning_path", tmp_path / "retrieval_tuning.json")
    monkeypatch.setattr(settings, "ui_config_path", ui_path)
    monkeypatch.setattr(settings, "openai_api_key", "")
    from api.main import app

    with TestClient(app) as c:
        yield c


def test_approve_runs_add_to_golden(client: TestClient):
    client.post(
        "/feedback",
        json={
            "user_id": "u1",
            "rating": 0,
            "question": "Q1",
            "answer_preview": "A1",
            "correction": "正确答案是 B",
        },
    )
    client.post("/admin/feedback/triage", json={"use_llm": False})
    fid = client.get("/admin/feedback").json()["items"][0]["id"]
    r = client.post(f"/admin/feedback/{fid}/approve")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "applied"
    assert body["action_results"]
    assert any(x.get("ok") for x in body["action_results"])
    assert settings.golden_jsonl_path.is_file()


def test_config_revisions_rollback(client: TestClient):
    fid = insert_feedback(user_id="u1", rating=0, question="cfg")
    enrich_feedback(fid, context_count=1, sources=["s.pdf"])
    save_triage_result(
        fid,
        issue_type="prompt",
        severity="medium",
        summary="cfg",
        human_review_required=True,
        suggested_actions=[
            {
                "action": "apply_config_patch",
                "confidence": 0.5,
                "patch": {"ui_config": {"kb_min_score": 0.42}},
            }
        ],
    )
    client.post(f"/admin/feedback/{fid}/approve")
    revs = client.get("/admin/feedback/config-revisions")
    assert revs.status_code == 200
    items = revs.json()["items"]
    assert len(items) >= 1
    rev_id = items[0]["id"]
    rb = client.post(f"/admin/feedback/config-revisions/{rev_id}/rollback")
    assert rb.status_code == 200
    ui = json.loads(settings.ui_config_path.read_text(encoding="utf-8"))
    assert ui["kb_min_score"] == 0.55
