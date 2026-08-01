"""TDD: exam chat security (ACL, answers leak, attempt ownership)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def exam_db(tmp_path, monkeypatch):
    """Single exam_bank DB for the test — path patched before any app/client setup."""
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    return store


@pytest.fixture()
def client(exam_db):
    from api.exam_router import router as exam_router

    app = FastAPI()
    app.include_router(exam_router)
    with TestClient(app) as c:
        yield c


def _seed_private_paper(store: Any):
    col = store.create_collection(
        name="私有·数学·高三",
        subject="数学",
        grade="高三",
        region="杭州",
        visibility="private",
        owner_user_id="alice",
    )
    q = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="1+1=?",
        options=["A. 1", "B. 2", "C. 3", "D. 4"],
        answer="B",
        quality_status="published",
    )
    sp = store.create_source_paper(
        collection_id=col["id"],
        title="私有卷",
        source_filename="private.docx",
        question_ids=[q["id"]],
    )
    return col, sp, q


def test_gate_inventory_hides_private_collection_from_other_user(exam_db):
    from exam_bank.chat_exam_gate import resolve_exam_chat_gate

    _seed_private_paper(exam_db)

    gate = resolve_exam_chat_gate("现在题库里有什么内容", reader_user_id="bob")
    assert gate is not None
    overview = gate.get("overview") or {}
    names = [c.get("name") or "" for c in overview.get("collections") or []]
    assert not any("私有" in n for n in names)
    assert overview.get("collection_count") == 0


def test_chat_get_paper_rejects_include_answers(client, exam_db):
    _, sp, _ = _seed_private_paper(exam_db)

    r = client.get(f"/api/exam/chat/papers/{sp['id']}?include_answers=true")
    assert r.status_code == 400
    detail = r.json().get("detail") or {}
    assert detail.get("error") == "include_answers_forbidden"


def test_client_reads_seeded_exam_db(client, exam_db):
    """Regression: HTTP client must use exam_db fixture path, not a second tmp_path."""
    col = exam_db.create_collection(name="公开库", subject="数学", grade="高三", region="浙江")
    sp = exam_db.create_source_paper(
        collection_id=col["id"],
        title="连通性卷",
        source_filename="ok.docx",
        question_ids=[],
    )

    r = client.get(f"/api/exam/chat/papers/{sp['id']}")
    assert r.status_code == 200
    assert r.json().get("title") == "连通性卷"


def test_submit_attempt_rejects_other_user(exam_db):
    from exam_bank.chat_paper import start_attempt, submit_attempt

    _, sp, q = _seed_private_paper(exam_db)

    started = start_attempt(sp["id"], user_id="alice")
    aid = started["attempt_id"]
    bad = submit_attempt(aid, answers={q["id"]: "B"}, user_id="bob")
    assert bad["ok"] is False
    assert bad.get("error") == "forbidden"


def test_gate_no_keywords_does_not_fallback_to_recent_papers(exam_db):
    from exam_bank.chat_exam_gate import resolve_exam_chat_gate

    col = exam_db.create_collection(name="公开库", subject="数学", grade="高三", region="浙江")
    exam_db.create_source_paper(
        collection_id=col["id"],
        title="某卷",
        source_filename="x.docx",
        question_ids=[],
    )

    gate = resolve_exam_chat_gate("开始答题，标准卷面")
    assert gate is not None
    assert gate["hit_count"] == 0
    assert "请" in gate["answer"] or "说明" in gate["answer"] or "哪" in gate["answer"]


def test_normalize_multi_answer_set():
    from exam_bank.chat_paper import normalize_objective_answer

    assert normalize_objective_answer("AB", "multi") == "AB"
    assert normalize_objective_answer("B,A", "multi") == "AB"
    assert normalize_objective_answer("A. 1, B. 2", "multi") == "AB"
