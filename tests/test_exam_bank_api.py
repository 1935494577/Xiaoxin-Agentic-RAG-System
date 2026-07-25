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
    assert set(body.get("export_formats") or []) == {"markdown", "docx", "pdf"}
    assert any(s["id"] == "数学" for s in body.get("subjects") or [])
    assert body.get("difficulty_bands")


def test_create_collection_duplicate_scope_api(client):
    a = client.post(
        "/api/exam/collections",
        json={
            "name": "互斥库",
            "subject": "数学",
            "grade": "初一",
            "region": "杭州",
            "visibility": "private",
            "owner_user_id": "zhan",
        },
    )
    assert a.status_code == 200
    b = client.post(
        "/api/exam/collections",
        json={
            "name": "另一个名字",
            "subject": "数学",
            "grade": "初一",
            "region": "杭州",
            "visibility": "private",
            "owner_user_id": "zhan",
        },
    )
    assert b.status_code == 409
    detail = b.json().get("detail") or {}
    assert detail.get("error") == "collection_scope_conflict" or "conflict" in str(detail).lower()


def test_create_collection_requires_region_api(client):
    r = client.post(
        "/api/exam/collections",
        json={"name": "无", "subject": "数学", "grade": "初一", "region": ""},
    )
    assert r.status_code == 400
    detail = r.json().get("detail") or {}
    assert "region" in str(detail).lower()


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


def test_exam_crud_and_ingest_api(client):
    c = client.post(
        "/api/exam/collections",
        json={"name": "导入库", "subject": "数学", "grade": "初二", "region": "某地"},
    )
    col_id = c.json()["id"]

    parsed = client.post(
        "/api/exam/ingest/parse",
        json={
            "text": "一、选择题\n1. 题一\nA. 1\nB. 2\n2. 题二\nA. 甲\nB. 乙\n",
            "subject": "数学",
            "use_llm": False,
        },
    )
    assert parsed.status_code == 200
    items = parsed.json()["items"]
    assert len(items) >= 2

    committed = client.post(
        "/api/exam/ingest/commit",
        json={
            "collection_id": col_id,
            "title": "卷A",
            "raw_text": "…",
            "quality_status": "published",
            "items": items,
        },
    )
    assert committed.status_code == 200
    sp_id = committed.json()["source_paper"]["id"]
    qid = committed.json()["questions"][0]["id"]

    upd = client.put(
        f"/api/exam/questions/{qid}",
        json={"stem": "改后题干", "answer": "A"},
    )
    assert upd.status_code == 200
    assert upd.json()["stem"] == "改后题干"

    applied = client.post(
        "/api/exam/ingest/apply-answers",
        json={"source_paper_id": sp_id, "answer_text": "1. A\n2. B\n"},
    )
    assert applied.status_code == 200
    assert applied.json()["updated"] >= 1

    assert client.delete(f"/api/exam/questions/{qid}").status_code == 200
    assert client.delete(f"/api/exam/collections/{col_id}").status_code == 200


def test_exam_paper_export_formats(client):
    c = client.post(
        "/api/exam/collections",
        json={"name": "导出API库", "subject": "数学", "grade": "初二", "region": "浙江"},
    )
    assert c.status_code == 200
    col_id = c.json()["id"]
    for i in range(3):
        q = client.post(
            "/api/exam/questions",
            json={
                "collection_id": col_id,
                "qtype": "choice",
                "difficulty": 3,
                "stem": f"题{i}",
                "options": ["A", "B"],
                "answer": "A",
                "quality_status": "published",
            },
        )
        assert q.status_code == 200

    paper = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": col_id,
            "title": "API导出卷",
            "include_answers": True,
            "spec": {"by_qtype": {"choice": 2}, "seed": 1},
        },
    )
    assert paper.status_code == 200
    pid = paper.json()["paper_id"]

    md = client.get(f"/api/exam/papers/{pid}/export", params={"format": "markdown"})
    assert md.status_code == 200
    assert "markdown" in (md.headers.get("content-type") or "")
    assert "API导出卷".encode("utf-8") in md.content

    docx = client.get(f"/api/exam/papers/{pid}/export", params={"format": "docx"})
    assert docx.status_code == 200
    assert docx.content[:2] == b"PK"

    pdf = client.get(f"/api/exam/papers/{pid}/export", params={"format": "pdf"})
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"

    bad = client.get(f"/api/exam/papers/{pid}/export", params={"format": "xlsx"})
    assert bad.status_code == 400
