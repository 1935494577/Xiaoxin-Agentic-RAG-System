"""TDD: ingest commits region/year/chapter for assemble closed loop."""

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

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "meta_loop.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_ingest_commit_writes_region_year_chapter(client):
    col = client.post(
        "/api/exam/collections",
        json={"name": "闭环库", "subject": "数学", "grade": "高一", "region": "浙江"},
    ).json()
    r = client.post(
        "/api/exam/ingest/commit",
        json={
            "collection_id": col["id"],
            "title": "2024浙江卷",
            "region": "浙江",
            "year": "2024",
            "quality_status": "published",
            "items": [
                {
                    "question_no": "1",
                    "qtype": "choice",
                    "stem": "集合题",
                    "options": ["A.1", "B.2"],
                    "answer": "A",
                    "knowledge_tags": ["集合"],
                    "chapter": "集合与常用逻辑用语",
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
    assert q["chapter"] == "集合与常用逻辑用语"

    inv = client.get(f"/api/exam/inventory?collection_id={col['id']}").json()
    chapters = {c["chapter"]: c["count"] for c in inv.get("by_chapter") or []}
    assert chapters.get("集合与常用逻辑用语") == 1
    assert "浙江" in inv["regions"]
    assert "2024" in inv["years"]


def test_meta_exposes_common_regions(client):
    r = client.get("/api/exam/meta")
    assert r.status_code == 200
    regions = r.json().get("common_regions") or []
    assert "浙江" in regions
    assert "北京" in regions
