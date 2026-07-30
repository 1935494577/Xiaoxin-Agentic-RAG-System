"""TDD: P1 natural-language assemble → by_qtype / by_qtype_band."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_parse_assemble_nl_basic():
    from exam_bank.nl_assemble import parse_assemble_nl

    r = parse_assemble_nl("高三数学浙江中等难度，选择 8 + 填空 4 + 解答 4")
    assert r["ok"] is True
    assert r["spec"]["by_qtype"]["choice"] == 8
    assert r["spec"]["by_qtype"]["fill"] == 4
    assert r["spec"]["by_qtype"]["short"] == 4
    # 中等难度 → 全部落入 mid 档
    bands = r["spec"]["by_qtype_band"]
    assert bands["choice"]["mid"] == 8
    assert bands["fill"]["mid"] == 4
    assert "高三" in r["title"] or "数学" in r["title"]


def test_parse_assemble_nl_per_band():
    from exam_bank.nl_assemble import parse_assemble_nl

    r = parse_assemble_nl("选择题5道（简单2中等2困难1），填空题3道简单1中等1困难1")
    assert r["ok"] is True
    assert r["spec"]["by_qtype"]["choice"] == 5
    assert r["spec"]["by_qtype_band"]["choice"] == {"easy": 2, "mid": 2, "hard": 1}
    assert r["spec"]["by_qtype"]["fill"] == 3
    assert r["spec"]["by_qtype_band"]["fill"] == {"easy": 1, "mid": 1, "hard": 1}


def test_parse_assemble_nl_empty():
    from exam_bank.nl_assemble import parse_assemble_nl

    r = parse_assemble_nl("随便聊聊")
    assert r["ok"] is False
    assert r["error"] == "nl_parse_empty"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from exam_bank import store

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "nl.db")
    store.init_exam_bank_db()
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


def test_assemble_nl_api_end_to_end(client):
    col = client.post(
        "/api/exam/collections",
        json={"name": "NL库", "subject": "数学", "grade": "高三", "region": "浙江"},
    ).json()
    cid = col["id"]
    for i, (qt, diff) in enumerate(
        [("choice", 3), ("choice", 3), ("fill", 3), ("fill", 3), ("short", 3), ("short", 3)]
    ):
        client.post(
            "/api/exam/questions",
            json={
                "collection_id": cid,
                "qtype": qt,
                "difficulty": diff,
                "stem": f"题{i+1}",
                "quality_status": "published",
            },
        )
    r = client.post(
        "/api/exam/papers/assemble-nl",
        json={
            "collection_id": cid,
            "text": "选择 2 + 填空 2 + 解答 2，中等难度",
            "include_answers": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert len(body["question_ids"]) == 6
    assert "姓名__________" in body["markdown"]
    assert body.get("parsed_spec")


def test_assemble_from_nl_soft_fallback_when_mid_short(tmp_path, monkeypatch):
    """中等档不够时默认 soft_fallback，仍应组出卷。"""
    from exam_bank import store
    from exam_bank.nl_assemble import assemble_from_nl

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "nl_fb.db")
    store.init_exam_bank_db()
    col = store.create_collection(
        name="兜底库", subject="数学", grade="高一", region="广东", visibility="tenant_shared"
    )
    # only 1 mid fill, but NL asks mid×4 for fill
    for i in range(4):
        store.create_question(
            collection_id=col["id"],
            qtype="choice",
            difficulty=3,
            stem=f"选{i}",
            quality_status="published",
        )
    store.create_question(
        collection_id=col["id"],
        qtype="fill",
        difficulty=3,
        stem="填1",
        quality_status="published",
    )
    for i in range(3):
        store.create_question(
            collection_id=col["id"],
            qtype="fill",
            difficulty=5,
            stem=f"填难{i}",
            quality_status="published",
        )
    for i in range(4):
        store.create_question(
            collection_id=col["id"],
            qtype="short",
            difficulty=3,
            stem=f"解{i}",
            quality_status="published",
        )
    r = assemble_from_nl(
        collection_id=col["id"],
        text="选择 4 + 填空 4 + 解答 4，中等难度",
        title="兜底卷",
    )
    assert r.get("ok") is True, r
    assert len(r.get("question_ids") or []) == 12
