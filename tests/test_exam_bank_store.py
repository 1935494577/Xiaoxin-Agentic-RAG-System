"""Exam bank store — TDD."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_create_collection_and_question(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    col = store.create_collection(
        name="某地-初二-数学",
        subject="数学",
        grade="初二",
        region="某地",
        description="侧重点测试",
    )
    assert col["id"]
    assert col["subject"] == "数学"
    assert col["grade"] == "初二"

    q = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        difficulty=3,
        stem="一次函数 y=kx+b 的图像一定经过？",
        options=["A. 原点", "B. 不一定", "C. y轴", "D. x轴"],
        answer="B",
        analysis="截距可为非零。",
        knowledge_tags=["一次函数", "图像"],
        region="某地",
        year="2024",
        quality_status="published",
    )
    assert q["id"]
    assert q["qtype"] == "choice"
    assert q["difficulty"] == 3
    assert "一次函数" in q["knowledge_tags"]

    listed, total = store.list_questions(collection_id=col["id"], status="published")
    assert total == 1
    assert len(listed) == 1
    assert listed[0]["stem"].startswith("一次函数")


def test_list_collections_filters_tenant(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    store.create_collection(name="A", subject="语文", grade="初一", region="东", tenant_id="internal")
    store.create_collection(name="B", subject="英语", grade="初一", region="西", tenant_id="other")
    rows = store.list_collections(tenant_id="internal")
    assert len(rows) == 1
    assert rows[0]["region"] == "东"
    assert "语文" in rows[0]["name"]


def test_create_collection_rejects_duplicate_scope_same_owner(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    store.create_collection(
        name="ignored",
        subject="数学",
        grade="初一",
        region="杭州",
        visibility="private",
        owner_user_id="zhan",
    )
    try:
        store.create_collection(
            name="other",
            subject="数学",
            grade="初一",
            region="杭州",
            visibility="private",
            owner_user_id="zhan",
        )
        assert False, "expected scope conflict"
    except ValueError as e:
        assert "collection_scope_conflict" in str(e)

    # different owner may reuse the same region×subject×grade privately
    other = store.create_collection(
        name="x",
        subject="数学",
        grade="初一",
        region="杭州",
        visibility="private",
        owner_user_id="other",
    )
    assert other["id"]

    # different grade ok
    ok = store.create_collection(
        name="x",
        subject="数学",
        grade="初二",
        region="杭州",
        visibility="private",
        owner_user_id="zhan",
    )
    assert ok["id"]

    # different region ok
    ok2 = store.create_collection(
        name="x",
        subject="数学",
        grade="初一",
        region="宁波",
        visibility="private",
        owner_user_id="zhan",
    )
    assert ok2["id"]


def test_create_collection_requires_region(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    try:
        store.create_collection(name="无地区", subject="数学", grade="初一", region="")
        assert False, "expected region_required"
    except ValueError as e:
        assert "region_required" in str(e)