"""TDD: region × subject × grade = one collection; ingest/assemble closed loop."""

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

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "region_scope.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_create_collection_requires_region(client):
    r = client.post(
        "/api/exam/collections",
        json={"name": "无地区", "subject": "数学", "grade": "高一", "region": ""},
    )
    assert r.status_code == 400
    assert "region" in str(r.json().get("detail", "")).lower()


def test_one_collection_per_region_subject_grade(client):
    body = {
        "name": "ignored",
        "subject": "数学",
        "grade": "高一",
        "region": "浙江",
        "owner_user_id": "u1",
        "visibility": "private",
    }
    a = client.post("/api/exam/collections", json=body)
    assert a.status_code == 200, a.text
    col = a.json()
    assert col["region"] == "浙江"
    assert "浙江" in col["name"] and "数学" in col["name"]

    b = client.post("/api/exam/collections", json=body)
    assert b.status_code == 409
    detail = b.json().get("detail") or {}
    if isinstance(detail, dict):
        assert detail.get("error") == "collection_scope_conflict"

    # 同科同年级但不同地区 → 可再建
    c = client.post(
        "/api/exam/collections",
        json={**body, "region": "江苏"},
    )
    assert c.status_code == 200, c.text
    assert c.json()["region"] == "江苏"
    assert c.json()["id"] != col["id"]


def test_list_collections_filter_region(client):
    for region in ("浙江", "江苏"):
        client.post(
            "/api/exam/collections",
            json={
                "name": "x",
                "subject": "数学",
                "grade": "高一",
                "region": region,
                "owner_user_id": "u1",
            },
        )
    all_rows = client.get("/api/exam/collections?reader_user_id=u1").json()["items"]
    assert len(all_rows) == 2
    zj = client.get(
        "/api/exam/collections?reader_user_id=u1&region=浙江"
    ).json()["items"]
    assert len(zj) == 1
    assert zj[0]["region"] == "浙江"


def test_ingest_forces_collection_region_and_assemble_scoped(client):
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
    # body 故意传错地区 → 仍以题库地区为准
    r = client.post(
        "/api/exam/ingest/commit",
        json={
            "collection_id": col["id"],
            "title": "2024浙江卷",
            "region": "江苏",
            "year": "2024",
            "quality_status": "published",
            "items": [
                {
                    "question_no": "1",
                    "qtype": "choice",
                    "stem": "浙题",
                    "options": ["A.1"],
                    "answer": "A",
                    "knowledge_tags": ["集合"],
                    "chapter": "集合",
                    "difficulty": 2,
                    "selected": True,
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    q = r.json()["questions"][0]
    assert q["region"] == "浙江"
    assert q["year"] == "2024"

    # 同库再入一题不同年份
    client.post(
        "/api/exam/ingest/commit",
        json={
            "collection_id": col["id"],
            "title": "2023卷",
            "year": "2023",
            "items": [
                {
                    "qtype": "fill",
                    "stem": "填空浙",
                    "answer": "1",
                    "knowledge_tags": ["函数"],
                    "difficulty": 3,
                    "selected": True,
                }
            ],
        },
    )

    paper = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": col["id"],
            "title": "浙江数学卷",
            "spec": {
                "by_qtype": {"choice": 1},
                "knowledge_tags_any": ["集合"],
                "years_any": ["2024"],
                "seed": 1,
            },
        },
    )
    assert paper.status_code == 200, paper.text
    body = paper.json()
    assert body["ok"] is True
    assert body["counts"]["choice"] == 1
    qid = body["question_ids"][0]
    got = client.get(f"/api/exam/questions/{qid}").json()
    assert got["region"] == "浙江"
    assert got["year"] == "2024"
    assert "集合" in (got.get("knowledge_tags") or [])


def test_purge_clears_all(client):
    client.post(
        "/api/exam/collections",
        json={
            "name": "x",
            "subject": "数学",
            "grade": "高一",
            "region": "浙江",
            "owner_user_id": "u1",
        },
    )
    assert client.get("/api/exam/collections?reader_user_id=u1").json()["total"] == 1
    p = client.post("/api/exam/admin/purge")
    assert p.status_code == 200, p.text
    assert p.json().get("ok") is True
    assert client.get("/api/exam/collections?reader_user_id=u1").json()["total"] == 0
