"""Feedback API Sprint D — evaluate endpoints."""

import json

import pytest
from fastapi.testclient import TestClient

from config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
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
    from api.main import app

    with TestClient(app) as c:
        yield c


def test_admin_run_evaluate(client: TestClient):
    r = client.post("/admin/feedback/evaluate", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["golden_rows"] == 1
    assert body["metrics"]


def test_admin_list_eval_reports(client: TestClient):
    client.post("/admin/feedback/evaluate", json={})
    r = client.get("/admin/feedback/eval-reports")
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_admin_export_eval_reports(client: TestClient):
    client.post("/admin/feedback/evaluate", json={})
    r = client.post("/admin/feedback/eval-reports/export")
    assert r.status_code == 200
    assert r.json()["exported"] >= 1
