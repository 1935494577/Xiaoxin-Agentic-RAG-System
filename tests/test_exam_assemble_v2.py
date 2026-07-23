"""Assemble v2: missing qtype message + difficulty bands."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _col(store):
    return store.create_collection(name="库", subject="数学", grade="初二", region="某地")


def test_missing_qtype_message(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = _col(store)
    store.create_question(
        collection_id=col["id"],
        qtype="choice",
        difficulty=3,
        stem="仅有选择",
        options=["A"],
        answer="A",
        quality_status="published",
    )
    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="缺填空",
        spec={"by_qtype": {"fill": 1}, "seed": 1},
    )
    assert r["ok"] is False
    assert r["error"] == "missing_qtype"
    assert "没有相应题型" in r["detail"]["message"]
    assert r["detail"]["qtype"] == "fill"


def test_by_difficulty_band(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = _col(store)
    for i, d in enumerate([1, 1, 3, 3, 3, 5, 5]):
        store.create_question(
            collection_id=col["id"],
            qtype="choice",
            difficulty=d,
            stem=f"题{i}",
            options=["A"],
            answer="A",
            quality_status="published",
        )
    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="难度卷",
        spec={
            "by_qtype": {"choice": 5},
            "by_difficulty_band": {"easy": 1, "mid": 2, "hard": 2},
            "seed": 3,
        },
    )
    assert r["ok"] is True
    assert len(r["question_ids"]) == 5


def test_custom_qtype_assemble(tmp_path, monkeypatch):
    from exam_bank import assemble, store
    from exam_bank.subject_catalog import normalize_qtype

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = _col(store)
    qt = normalize_qtype("证明题")
    store.create_question(
        collection_id=col["id"],
        qtype=qt,
        difficulty=4,
        stem="证明：…",
        options=[],
        answer="略",
        quality_status="published",
    )
    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="自定义",
        spec={"by_qtype": {qt: 1}, "seed": 1},
    )
    assert r["ok"] is True
