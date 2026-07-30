"""TDD: exam-bank inventory intent (not knowledge base)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_is_exam_inventory_intent():
    from exam_bank.exam_intent import is_exam_inventory_intent, is_exam_take_intent

    assert is_exam_inventory_intent("现在题库里有什么内容")
    assert is_exam_inventory_intent("题库有哪些试卷")
    assert is_exam_inventory_intent("看看试卷题库概况")
    assert is_exam_inventory_intent("题库里有几套卷")
    assert not is_exam_inventory_intent("知识库里有什么文档")
    assert not is_exam_inventory_intent("员工手册怎么写")
    # take-exam stays take, not inventory-only
    assert is_exam_take_intent("把题库里的浙江卷拿出来做")
    assert not is_exam_inventory_intent("把题库里的浙江卷拿出来做")


def test_gate_inventory_lists_exam_bank_not_kb(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.chat_exam_gate import resolve_exam_chat_gate

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = store.create_collection(
        name="浙江·数学·高三", subject="数学", grade="高三", region="浙江"
    )
    store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="1+1=?",
        options=["A. 1", "B. 2", "C. 3", "D. 4"],
        answer="B",
        analysis="a",
        quality_status="published",
    )
    sp = store.create_source_paper(
        collection_id=col["id"],
        title="2024年高考数学新课标I卷",
        source_filename="math.docx",
        question_ids=["q1"],
    )

    gate = resolve_exam_chat_gate("现在题库里有什么内容")
    assert gate is not None
    assert gate["handled"] is True
    assert gate.get("mode") == "inventory"
    ans = gate["answer"]
    assert "题库" in ans
    assert "知识库" in ans  # clarify distinction
    assert "超脑进化" not in ans
    assert "浙江" in ans or "数学" in ans
    assert "2024" in ans or sp["title"][:4] in ans
    assert "知识文档" not in ans or "不是知识库" in ans or "向量" in ans


def test_gate_inventory_empty(tmp_path, monkeypatch):
    from exam_bank import store
    from exam_bank.chat_exam_gate import resolve_exam_chat_gate

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    gate = resolve_exam_chat_gate("题库里有什么")
    assert gate is not None
    assert gate["handled"] is True
    assert gate["hit_count"] == 0
    assert "试卷题库" in gate["answer"] or "试卷入库" in gate["answer"]