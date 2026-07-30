"""TDD: P3 question search by stem / tags (q=)."""

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

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "p3.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_list_questions_q_searches_stem_and_tags(client):
    col = client.post(
        "/api/exam/collections",
        json={"name": "检索库", "subject": "数学", "grade": "高三"},
    ).json()
    cid = col["id"]
    client.post(
        "/api/exam/questions",
        json={
            "collection_id": cid,
            "qtype": "choice",
            "stem": "已知集合 A={1}",
            "knowledge_tags": ["集合"],
            "quality_status": "published",
        },
    )
    client.post(
        "/api/exam/questions",
        json={
            "collection_id": cid,
            "qtype": "fill",
            "stem": "求导 f(x)=x^2",
            "knowledge_tags": ["导数"],
            "quality_status": "published",
        },
    )
    by_stem = client.get(f"/api/exam/questions?collection_id={cid}&q=集合")
    assert by_stem.status_code == 200
    items = by_stem.json()["items"]
    assert len(items) == 1
    assert "集合" in items[0]["stem"]

    by_tag = client.get(f"/api/exam/questions?collection_id={cid}&q=导数")
    assert by_tag.status_code == 200
    assert len(by_tag.json()["items"]) == 1
    assert "求导" in by_tag.json()["items"][0]["stem"]
