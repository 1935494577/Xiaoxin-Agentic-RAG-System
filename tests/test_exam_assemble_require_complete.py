"""TDD: assemble defaults to excluding incomplete questions."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_assemble_skips_incomplete_by_default(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = store.create_collection(name="库", subject="数学", grade="高三", region="浙江")
    store.create_question(
        collection_id=col["id"],
        qtype="choice",
        difficulty=3,
        stem="残缺题",
        options=["A", "B", "C", "D"],
        answer="",
        quality_status="published",
    )
    good = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        difficulty=3,
        stem="完整题 1+1",
        options=["A. 1", "B. 2", "C. 3", "D. 4"],
        answer="B",
        quality_status="published",
    )
    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="t",
        spec={"by_qtype": {"choice": 1}, "seed": 1},
    )
    assert r["ok"] is True
    ids = [q["id"] for q in r["questions"]]
    assert ids == [good["id"]]


def test_assemble_can_include_incomplete_when_disabled(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = store.create_collection(name="库", subject="数学", grade="高三", region="浙江")
    bad = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        difficulty=3,
        stem="残缺",
        options=["A", "B", "C", "D"],
        answer="",
        quality_status="published",
    )
    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="t",
        spec={"by_qtype": {"choice": 1}, "seed": 1, "require_complete": False},
    )
    assert r["ok"] is True
    assert r["questions"][0]["id"] == bad["id"]
