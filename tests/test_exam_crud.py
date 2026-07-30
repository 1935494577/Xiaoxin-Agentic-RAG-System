"""TDD: exam bank update/delete question and collection."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_update_and_delete_question(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    col = store.create_collection(name="库", subject="数学", grade="初二", region="浙江")
    q = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="原题干",
        options=["A. 1", "B. 2"],
        answer="A",
        quality_status="published",
    )
    updated = store.update_question(
        q["id"],
        stem="新题干",
        answer="B",
        difficulty=4,
        options=["A. 1", "B. 2", "C. 3"],
    )
    assert updated["stem"] == "新题干"
    assert updated["answer"] == "B"
    assert updated["difficulty"] == 4
    assert len(updated["options"]) == 3

    assert store.delete_question(q["id"]) is True
    assert store.get_question(q["id"]) is None


def test_delete_collection_cascades_questions(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    col = store.create_collection(name="库2", subject="数学", grade="初二", region="江苏")
    q = store.create_question(
        collection_id=col["id"],
        qtype="fill",
        stem="填空",
        quality_status="published",
    )
    assert store.delete_collection(col["id"]) is True
    assert store.get_collection(col["id"]) is None
    assert store.get_question(q["id"]) is None
