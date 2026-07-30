"""TDD: P4 lesson plan from assembled paper."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_render_lesson_outline_rules():
    from exam_bank.lesson import render_lesson_outline

    md = render_lesson_outline(
        title="集合专项卷",
        questions=[
            {
                "qtype": "choice",
                "stem": "已知集合 A",
                "knowledge_tags": ["集合"],
                "difficulty": 2,
                "answer": "A",
                "analysis": "定义",
            },
            {
                "qtype": "fill",
                "stem": "1+1",
                "knowledge_tags": ["运算"],
                "difficulty": 1,
                "answer": "2",
                "analysis": "",
            },
        ],
    )
    assert "教案大纲" in md
    assert "集合专项卷" in md
    assert "集合" in md
    assert "教学目标" in md
    assert "例题精讲" in md


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from exam_bank import store

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "p4.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_lesson_api_from_paper(client):
    col = client.post(
        "/api/exam/collections",
        json={"name": "教案库", "subject": "数学", "grade": "高三"},
    ).json()
    cid = col["id"]
    for i in range(2):
        client.post(
            "/api/exam/questions",
            json={
                "collection_id": cid,
                "qtype": "choice",
                "stem": f"题{i}",
                "knowledge_tags": ["集合"],
                "difficulty": 3,
                "quality_status": "published",
            },
        )
    paper = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": cid,
            "title": "集合练",
            "include_answers": True,
            "spec": {"by_qtype": {"choice": 2}},
        },
    ).json()
    r = client.post(f"/api/exam/papers/{paper['paper_id']}/lesson")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert "教案大纲" in body["markdown"]
    assert body["paper_id"] == paper["paper_id"]
