"""TDD: exam take intent + chat exam gate."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_is_exam_take_intent():
    from exam_bank.exam_intent import extract_exam_search_query, is_exam_take_intent

    assert is_exam_take_intent("将入库的浙江高三卷子拿出来给我做")
    assert is_exam_take_intent("把 2024 新课标卷拿出来做")
    assert is_exam_take_intent("开始答题，标准卷面")
    assert not is_exam_take_intent("员工手册第三章怎么写")
    assert not is_exam_take_intent("今天天气怎么样")

    q = extract_exam_search_query("将入库的浙江高三卷子拿出来给我做")
    assert "浙江" in q
    assert "高三" in q


def test_gate_finds_paper_by_collection_region(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.chat_exam_gate import resolve_exam_chat_gate

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    col = store.create_collection(
        name="浙江·数学·高三", subject="数学", grade="高三", region="浙江"
    )
    sp = store.create_source_paper(
        collection_id=col["id"],
        title="2024年高考数学新课标I卷",
        source_filename="math.docx",
        question_ids=["q1"],
    )

    gate = resolve_exam_chat_gate("将入库的浙江高三卷子拿出来给我做")
    assert gate is not None
    assert gate["handled"] is True
    assert gate["hit_count"] >= 1
    ids = []
    for b in gate.get("ui_blocks") or []:
        if b.get("type") == "exam_paper":
            ids.append(b["source_paper_id"])
        if b.get("type") == "exam_candidates":
            ids.extend(i["id"] for i in b.get("items") or [])
    assert sp["id"] in ids or gate["hit_count"] == 1


def test_gate_skips_non_exam_question(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.chat_exam_gate import resolve_exam_chat_gate

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    assert resolve_exam_chat_gate("请假制度是什么") is None
