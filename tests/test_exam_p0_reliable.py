"""TDD: P0 exam LLM readiness + ingest commit difficulty."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def exam_client(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_p0.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_llm_status_reports_unconfigured(monkeypatch, exam_client):
    monkeypatch.setattr(
        "exam_bank.llm_client.build_openai_client",
        lambda timeout_sec=30.0: (None, {"source": "none", "model": ""}),
    )
    r = exam_client.get("/api/exam/llm-status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["configured"] is False
    assert "message" in body


def test_llm_status_reports_configured(monkeypatch, exam_client):
    class _Fake:
        pass

    monkeypatch.setattr(
        "exam_bank.llm_client.build_openai_client",
        lambda timeout_sec=30.0: (
            _Fake(),
            {
                "source": "env",
                "model": "deepseek-v4-flash",
                "chat_model": "deepseek-v4-flash",
                "routing_model": "deepseek-v4-flash",
                "llm_api_base": "https://x",
            },
        ),
    )
    r = exam_client.get("/api/exam/llm-status")
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is True
    assert body["model"] == "deepseek-v4-flash"


def test_ingest_commit_persists_difficulty_and_published(exam_client):
    col = exam_client.post(
        "/api/exam/collections",
        json={"name": "P0库", "subject": "数学", "grade": "高三", "region": "浙江"},
    ).json()
    r = exam_client.post(
        "/api/exam/ingest/commit",
        json={
            "collection_id": col["id"],
            "title": "样卷",
            "quality_status": "published",
            "items": [
                {
                    "question_no": "1",
                    "qtype": "choice",
                    "stem": "1+1=( )",
                    "options": ["A. 1", "B. 2"],
                    "answer": "B",
                    "analysis": "",
                    "knowledge_tags": ["运算"],
                    "difficulty": 2,
                    "selected": True,
                }
            ],
        },
    )
    assert r.status_code == 200
    qs = r.json()["questions"]
    assert len(qs) == 1
    assert qs[0]["difficulty"] == 2
    assert qs[0]["quality_status"] == "published"
    assert "运算" in qs[0]["knowledge_tags"]
