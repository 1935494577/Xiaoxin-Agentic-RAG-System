"""Exam paper assemble — TDD."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _seed_bank(store, n_choice=5, n_fill=3):
    col = store.create_collection(name="库", subject="数学", grade="初二", region="某地")
    ids = []
    for i in range(n_choice):
        q = store.create_question(
            collection_id=col["id"],
            qtype="choice",
            difficulty=2 + (i % 3),
            stem=f"选择题{i+1}",
            options=["A", "B", "C", "D"],
            answer="A",
            analysis="解析",
            knowledge_tags=["一次函数"] if i % 2 == 0 else ["几何"],
            quality_status="published",
        )
        ids.append(q["id"])
    for i in range(n_fill):
        q = store.create_question(
            collection_id=col["id"],
            qtype="fill",
            difficulty=3,
            stem=f"填空题{i+1}",
            options=[],
            answer="42",
            analysis="",
            knowledge_tags=["一次函数"],
            quality_status="published",
        )
        ids.append(q["id"])
    # draft should be ignored
    store.create_question(
        collection_id=col["id"],
        qtype="choice",
        difficulty=3,
        stem="草稿题",
        options=["A"],
        answer="A",
        quality_status="draft",
    )
    return col, ids


def test_assemble_success_deterministic(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col, _ = _seed_bank(store)

    r1 = assemble.assemble_paper(
        collection_id=col["id"],
        title="模拟卷A",
        spec={"by_qtype": {"choice": 3, "fill": 2}, "difficulty_min": 1, "difficulty_max": 5, "seed": 7},
        include_answers=True,
    )
    r2 = assemble.assemble_paper(
        collection_id=col["id"],
        title="模拟卷A",
        spec={"by_qtype": {"choice": 3, "fill": 2}, "difficulty_min": 1, "difficulty_max": 5, "seed": 7},
        include_answers=True,
    )
    assert r1["ok"] is True
    assert r1["question_ids"] == r2["question_ids"]
    assert r1["counts"]["choice"] == 3
    assert r1["counts"]["fill"] == 2
    assert "选择题" in r1["markdown"]
    assert "答案与解析" in r1["markdown"]
    assert store.get_paper(r1["paper_id"]) is not None


def test_assemble_insufficient(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col, _ = _seed_bank(store, n_choice=2, n_fill=1)

    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="不足",
        spec={"by_qtype": {"choice": 5}, "seed": 1},
    )
    assert r["ok"] is False
    assert r["error"] == "insufficient_questions"
    assert r["detail"]["qtype"] == "choice"
    assert r["detail"]["need"] == 5
    assert r["detail"]["have"] == 2
