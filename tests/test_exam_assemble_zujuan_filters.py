"""TDD: Zujuan-style assemble filters — inventory tags/years + region-scoped collections."""

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

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "zujuan.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def _seed_region(client, region: str, rows: list[tuple]) -> str:
    col = client.post(
        "/api/exam/collections",
        json={
            "name": "x",
            "subject": "数学",
            "grade": "高一",
            "region": region,
            "owner_user_id": "u1",
        },
    ).json()
    cid = col["id"]
    for stem, qt, tags, year, diff in rows:
        client.post(
            "/api/exam/questions",
            json={
                "collection_id": cid,
                "qtype": qt,
                "stem": stem,
                "knowledge_tags": tags,
                "year": year,
                "difficulty": diff,
                "quality_status": "published",
            },
        )
    return cid


def test_inventory_returns_by_tag_regions_years(client):
    cid = _seed_region(
        client,
        "浙江",
        [
            ("集合题浙", "choice", ["集合"], "2024", 3),
            ("奇偶题浙", "choice", ["奇偶性"], "2023", 2),
            ("函数填空", "fill", ["函数"], "2024", 3),
        ],
    )
    r = client.get(f"/api/exam/inventory?collection_id={cid}")
    assert r.status_code == 200
    body = r.json()
    tags = {row["tag"]: row["count"] for row in body.get("by_tag") or []}
    assert tags.get("集合") == 1
    assert tags.get("奇偶性") == 1
    assert body.get("regions") == ["浙江"]
    assert "2024" in (body.get("years") or [])
    assert "2023" in (body.get("years") or [])


def test_assemble_filters_region_locked_and_tags(client):
    cid = _seed_region(
        client,
        "浙江",
        [
            ("集合题浙", "choice", ["集合"], "2024", 3),
            ("奇偶题浙", "choice", ["奇偶性"], "2023", 2),
            ("集合填空", "fill", ["集合"], "2024", 3),
        ],
    )
    r = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": cid,
            "title": "浙江集合卷",
            "spec": {
                "by_qtype": {"choice": 1},
                "knowledge_tags_any": ["集合"],
                "seed": 1,
            },
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["counts"]["choice"] == 1
    q = client.get(f"/api/exam/questions/{body['question_ids'][0]}").json()
    assert q["region"] == "浙江"
    assert "集合" in (q.get("knowledge_tags") or [])


def test_assemble_filters_year(client):
    cid = _seed_region(
        client,
        "浙江",
        [
            ("集合题浙", "choice", ["集合"], "2024", 3),
            ("旧题", "choice", ["集合"], "2022", 3),
            ("填空24", "fill", ["集合"], "2024", 3),
        ],
    )
    r = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": cid,
            "title": "2024卷",
            "include_answers": False,
            "spec": {
                "by_qtype": {"choice": 1, "fill": 1},
                "years_any": ["2024"],
            },
        },
    )
    assert r.status_code == 200, r.text
    md = r.json()["markdown"]
    assert "集合题浙" in md or "填空24" in md
    assert "旧题" not in md


def test_inventory_filtered_by_tag_and_year(client):
    cid = _seed_region(
        client,
        "浙江",
        [
            ("集合题浙", "choice", ["集合"], "2024", 3),
            ("奇偶题浙", "choice", ["奇偶性"], "2023", 2),
            ("集合填空", "fill", ["集合"], "2024", 3),
        ],
    )
    r = client.get(
        f"/api/exam/inventory?collection_id={cid}&tag=集合&year=2024"
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("total_all") == 3
    assert body.get("total") == 2
    assert body["by_qtype"].get("choice") == 1
    assert body["by_qtype"].get("fill") == 1
    tags = {row["tag"]: row["count"] for row in body.get("by_tag") or []}
    assert tags.get("集合") == 2


def test_assemble_filters_chapter(client):
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
    cid = col["id"]
    client.post(
        "/api/exam/questions",
        json={
            "collection_id": cid,
            "qtype": "choice",
            "stem": "集合章题",
            "chapter": "集合与常用逻辑用语",
            "knowledge_tags": ["集合"],
            "quality_status": "published",
        },
    )
    client.post(
        "/api/exam/questions",
        json={
            "collection_id": cid,
            "qtype": "choice",
            "stem": "函数章题",
            "chapter": "函数概念与性质",
            "knowledge_tags": ["函数"],
            "quality_status": "published",
        },
    )
    r = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": cid,
            "title": "集合章卷",
            "spec": {
                "by_qtype": {"choice": 1},
                "chapters_any": ["集合与常用逻辑用语"],
                "seed": 1,
            },
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    q = client.get(f"/api/exam/questions/{body['question_ids'][0]}").json()
    assert q["chapter"] == "集合与常用逻辑用语"
    assert q["region"] == "浙江"
