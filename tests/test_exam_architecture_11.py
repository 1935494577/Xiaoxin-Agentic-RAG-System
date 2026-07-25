"""TDD: soft fallback when assemble filters are too strict."""

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

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "fallback.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def _seed(client) -> str:
    col = client.post(
        "/api/exam/collections",
        json={
            "name": "x",
            "subject": "数学",
            "grade": "初三",
            "region": "浙江",
            "owner_user_id": "u1",
        },
    ).json()
    cid = col["id"]
    for stem, tags, year in (
        ("勾股1", ["勾股定理"], "2024"),
        ("勾股2", ["勾股定理"], "2023"),
        ("相似1", ["相似三角形"], "2024"),
    ):
        client.post(
            "/api/exam/questions",
            json={
                "collection_id": cid,
                "qtype": "choice",
                "stem": stem,
                "knowledge_tags": tags,
                "year": year,
                "difficulty": 3,
                "quality_status": "published",
            },
        )
    return cid


def test_auto_generate_soft_fallback_relaxes_year(client):
    cid = _seed(client)
    # 只要 2022 年 → 空；开启兜底后应放宽年份拿到题
    r = client.post(
        "/api/exam/papers/auto-generate",
        json={
            "collection_id": cid,
            "title": "兜底卷",
            "spec": {
                "by_qtype": {"choice": 2},
                "knowledge_tags_any": ["勾股定理"],
                "years_any": ["2022"],
                "soft_fallback": True,
                "seed": 1,
            },
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert len(body.get("questions") or []) == 2
    assert body.get("fallback_applied") is True
    assert any("year" in str(x).lower() or "年份" in str(x) for x in (body.get("fallback_notes") or []))


def test_question_has_difficulty_coef_and_cognitive(client):
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
    q = client.post(
        "/api/exam/questions",
        json={
            "collection_id": col["id"],
            "qtype": "choice",
            "stem": "元数据题",
            "difficulty": 2,
            "difficulty_coef": 0.85,
            "cognitive_level": "apply",
            "discrimination": 0.4,
            "textbook_version": "人教A版",
            "quality_status": "published",
        },
    )
    assert q.status_code == 200, q.text
    body = q.json()
    assert abs(float(body["difficulty_coef"]) - 0.85) < 1e-6
    assert body["cognitive_level"] == "apply"
    assert body.get("textbook_version") == "人教A版"
