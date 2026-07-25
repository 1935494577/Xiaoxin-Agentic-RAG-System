"""TDD: P2 assemble filter by knowledge_tags_any."""

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

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "p2.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_assemble_filters_knowledge_tags(client):
    col = client.post(
        "/api/exam/collections",
        json={"name": "标签库", "subject": "数学", "grade": "高三"},
    ).json()
    cid = col["id"]
    for stem, tags in [
        ("集合题A", ["集合"]),
        ("集合题B", ["集合"]),
        ("函数题", ["函数"]),
    ]:
        client.post(
            "/api/exam/questions",
            json={
                "collection_id": cid,
                "qtype": "choice",
                "difficulty": 3,
                "stem": stem,
                "knowledge_tags": tags,
                "quality_status": "published",
            },
        )
    r = client.post(
        "/api/exam/papers/assemble",
        json={
            "collection_id": cid,
            "title": "集合专项",
            "include_answers": False,
            "spec": {"by_qtype": {"choice": 2}, "knowledge_tags_any": ["集合"]},
        },
    )
    assert r.status_code == 200, r.text
    md = r.json()["markdown"]
    assert "集合题" in md
    assert "函数题" not in md
