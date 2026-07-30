"""Assemble returns full question objects for basket / card preview."""

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

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "basket.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_assemble_returns_questions_for_basket(client):
    col = client.post(
        "/api/exam/collections",
        json={
            "name": "x",
            "subject": "数学",
            "grade": "高一",
            "region": "浙江",
            "owner_user_id": "u1",
        },
    ).json()
    client.post(
        "/api/exam/ingest/commit",
        json={
            "collection_id": col["id"],
            "title": "2024浙江卷",
            "year": "2024",
            "items": [
                {
                    "qtype": "choice",
                    "stem": "集合题干",
                    "options": ["A.1", "B.2"],
                    "answer": "A",
                    "analysis": "略",
                    "knowledge_tags": ["集合"],
                    "chapter": "集合",
                    "difficulty": 2,
                    "selected": True,
                },
                {
                    "qtype": "fill",
                    "stem": "填空题干",
                    "answer": "1",
                    "knowledge_tags": ["函数"],
                    "difficulty": 3,
                    "selected": True,
                },
            ],
        },
    )
    r = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": col["id"],
            "title": "测卷",
            "spec": {"by_qtype": {"choice": 1, "fill": 1}, "seed": 1},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    qs = body.get("questions") or []
    assert len(qs) == 2
    assert {q["qtype"] for q in qs} == {"choice", "fill"}
    assert all(q.get("region") == "浙江" for q in qs)
    assert any(q.get("source_paper_id") for q in qs)


def test_paper_from_questions_basket_finalize(client):
    col = client.post(
        "/api/exam/collections",
        json={
            "name": "x",
            "subject": "数学",
            "grade": "高一",
            "region": "浙江",
            "owner_user_id": "u1",
        },
    ).json()
    commit = client.post(
        "/api/exam/ingest/commit",
        json={
            "collection_id": col["id"],
            "title": "源卷",
            "year": "2024",
            "items": [
                {
                    "qtype": "choice",
                    "stem": "题A",
                    "options": ["A.1"],
                    "answer": "A",
                    "selected": True,
                },
                {
                    "qtype": "choice",
                    "stem": "题B",
                    "options": ["A.2"],
                    "answer": "A",
                    "selected": True,
                },
            ],
        },
    ).json()
    qids = [q["id"] for q in commit["questions"]]
    r = client.post(
        "/api/exam/papers/from-questions",
        json={
            "collection_id": col["id"],
            "title": "自选卷",
            "question_ids": [qids[1]],
            "include_answers": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["question_ids"] == [qids[1]]
    assert "题B" in body["markdown"]
    assert "题A" not in body["markdown"]
