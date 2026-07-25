"""TDD: LLM complete incomplete exam questions API."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

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


def test_list_questions_annotates_incomplete(client):
    from exam_bank import store

    col = store.create_collection(name="t", subject="数学", grade="高三", region="浙江")
    store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="函数图像是()",
        options=["A", "B", "C", "D"],
        answer="",
        quality_status="published",
    )
    r = client.get("/api/exam/questions", params={"collection_id": col["id"], "status": "all"})
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["incomplete"] is True
    assert "options" in item["incomplete_reasons"]


def test_llm_complete_question_updates_fields(client):
    from exam_bank import store

    col = store.create_collection(name="t", subject="数学", grade="高三", region="浙江")
    q = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="1+1=()",
        options=["A", "B", "C", "D"],
        answer="",
        quality_status="published",
    )
    fake = {
        "ok": True,
        "fields": {
            "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
            "answer": "B",
            "analysis": "1+1=2",
        },
        "model": "test",
        "reasons": ["options", "answer"],
    }
    with patch(
        "exam_bank.llm_ingest.complete_question_fields_with_llm",
        return_value=fake,
    ):
        r = client.post(f"/api/exam/questions/{q['id']}/llm-complete")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["question"]["answer"] == "B"
    assert len(body["question"]["options"]) == 4
    assert "A. 1" in body["question"]["options"][0]


def test_llm_complete_batch_collection(client):
    from exam_bank import store

    col = store.create_collection(name="t", subject="数学", grade="高三", region="浙江")
    store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="题1",
        options=["A", "B"],
        answer="",
        quality_status="published",
    )
    store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="题2完整",
        options=["A. 1", "B. 2", "C. 3", "D. 4"],
        answer="A",
        quality_status="published",
    )
    fake = {
        "ok": True,
        "fields": {"options": ["A. x", "B. y", "C. z", "D. w"], "answer": "A"},
        "model": "test",
        "reasons": ["options", "answer"],
    }
    with patch(
        "exam_bank.llm_ingest.complete_question_fields_with_llm",
        return_value=fake,
    ):
        r = client.post(
            f"/api/exam/collections/{col['id']}/llm-complete-incomplete",
            params={"limit": 5},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["attempted"] == 1
    assert body["updated"] == 1
