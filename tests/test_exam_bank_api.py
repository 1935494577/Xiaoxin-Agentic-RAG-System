"""Exam bank HTTP API — TDD (router-only app, no full lifespan)."""

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
def client(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    from api.exam_router import router as exam_router

    app = FastAPI()
    app.include_router(exam_router)
    with TestClient(app) as c:
        yield c


def test_exam_meta(client):
    r = client.get("/api/exam/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert "choice" in body["qtypes"]
    assert "exam_assemble" in body["scene_presets"]
    assert any(s["id"] == "数学" for s in body.get("subjects") or [])
    assert body.get("difficulty_bands")


def test_detect_sections_api(client):
    r = client.post(
        "/api/exam/detect-sections",
        json={
            "text": "一、选择题\n1.a\n二、填空题\n2.b\n三、解答题\n3.c",
            "subject": "数学",
            "grade": "初二",
            "use_llm": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    secs = body["sections"]
    assert len(secs) >= 2
    assert {s["qtype"] for s in secs} >= {"choice", "fill"}
    assert body["router"] == "rules"


def test_exam_collection_question_assemble_flow(client):
    c = client.post(
        "/api/exam/collections",
        json={"name": "库", "subject": "数学", "grade": "初二", "region": "某地"},
    )
    assert c.status_code == 200
    col_id = c.json()["id"]

    for i in range(4):
        q = client.post(
            "/api/exam/questions",
            json={
                "collection_id": col_id,
                "qtype": "choice",
                "difficulty": 3,
                "stem": f"题{i}",
                "options": ["A", "B"],
                "answer": "A",
                "knowledge_tags": ["代数"],
                "quality_status": "published",
            },
        )
        assert q.status_code == 200

    listed = client.get(f"/api/exam/questions?collection_id={col_id}&status=published")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 4

    paper = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": col_id,
            "title": "卷1",
            "include_answers": True,
            "spec": {"by_qtype": {"choice": 3}, "seed": 1},
        },
    )
    assert paper.status_code == 200
    body = paper.json()
    assert body["ok"] is True
    assert len(body["question_ids"]) == 3
    assert body["markdown"]

    got = client.get(f"/api/exam/papers/{body['paper_id']}")
    assert got.status_code == 200
    assert got.json()["id"] == body["paper_id"]
