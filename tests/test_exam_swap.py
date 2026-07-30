"""TDD: swap question candidates for assemble fine-tuning."""

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

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "swap.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def _seed(client) -> tuple[str, list[str]]:
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
    ids = []
    for stem, tags, diff in (
        ("勾股A", ["勾股定理"], 3),
        ("勾股B", ["勾股定理"], 3),
        ("勾股C", ["勾股定理"], 2),
        ("相似X", ["相似三角形"], 3),
    ):
        q = client.post(
            "/api/exam/questions",
            json={
                "collection_id": cid,
                "qtype": "choice",
                "stem": stem,
                "knowledge_tags": tags,
                "difficulty": diff,
                "quality_status": "published",
            },
        ).json()
        ids.append(q["id"])
    return cid, ids


def test_swap_returns_same_tag_alternatives(client):
    cid, ids = _seed(client)
    r = client.post(
        "/api/exam/questions/swap",
        json={
            "collection_id": cid,
            "question_id": ids[0],
            "exclude_ids": [ids[0]],
            "limit": 5,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    cands = body.get("candidates") or []
    assert len(cands) >= 2
    stems = {c["stem"] for c in cands}
    assert "勾股B" in stems or "勾股C" in stems
    assert "相似X" not in stems  # different tag preferred out


def test_swap_relaxes_when_no_tag_match(client):
    cid, ids = _seed(client)
    # only one 相似 — exclude self → soft fallback to same qtype
    r = client.post(
        "/api/exam/questions/swap",
        json={
            "collection_id": cid,
            "question_id": ids[3],
            "exclude_ids": [ids[3]],
            "limit": 5,
            "soft_fallback": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert len(body.get("candidates") or []) >= 1
    assert body.get("fallback_applied") is True
