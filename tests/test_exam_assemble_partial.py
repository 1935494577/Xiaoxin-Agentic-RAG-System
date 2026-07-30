"""TDD: no difficulty → random pool; soft_fallback caps to stock."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_soft_fallback_caps_to_available_stock(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = store.create_collection(name="库", subject="数学", grade="高三", region="浙江")
    for i in range(5):
        store.create_question(
            collection_id=col["id"],
            qtype="choice",
            difficulty=3,
            stem=f"选择{i}",
            options=["A. 1", "B. 2", "C. 3", "D. 4"],
            answer="A",
            analysis="a",
            quality_status="published",
        )

    # Without soft: fail
    hard = assemble.assemble_paper(
        collection_id=col["id"],
        title="硬",
        spec={"by_qtype": {"choice": 11}, "seed": 1, "soft_fallback": False},
    )
    assert hard["ok"] is False
    assert hard["error"] == "insufficient_questions"

    # With soft: use the 5 in bank
    soft = assemble.assemble_paper(
        collection_id=col["id"],
        title="软",
        spec={"by_qtype": {"choice": 11}, "seed": 1, "soft_fallback": True},
    )
    assert soft["ok"] is True
    assert len(soft["question_ids"]) == 5
    assert soft.get("fallback_applied") is True
    assert any("实际" in n or "可用" in n for n in (soft.get("fallback_notes") or []))


def test_no_band_picks_randomly_across_difficulties(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = store.create_collection(name="库", subject="数学", grade="高三", region="浙江")
    for i, d in enumerate([1, 2, 3, 4, 5]):
        store.create_question(
            collection_id=col["id"],
            qtype="choice",
            difficulty=d,
            stem=f"选择{i}",
            options=["A. 1", "B. 2", "C. 3", "D. 4"],
            answer="A",
            analysis="a",
            quality_status="published",
        )

    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="随机",
        spec={"by_qtype": {"choice": 5}, "seed": 7},  # no bands
    )
    assert r["ok"] is True
    diffs = sorted(int(q["difficulty"]) for q in r["questions"])
    assert diffs == [1, 2, 3, 4, 5]


def test_empty_region_not_excluded_by_collection_region_lock(tmp_path, monkeypatch):
    from exam_bank import assemble, store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    col = store.create_collection(name="库", subject="数学", grade="高三", region="浙江")
    for i in range(3):
        store.create_question(
            collection_id=col["id"],
            qtype="choice",
            difficulty=3,
            stem=f"选择{i}",
            options=["A. 1", "B. 2", "C. 3", "D. 4"],
            answer="A",
            analysis="a",
            region="",  # 未标注地区
            quality_status="published",
        )

    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="地区",
        spec={
            "by_qtype": {"choice": 3},
            "regions_any": ["浙江"],
            "seed": 1,
            "soft_fallback": False,
        },
    )
    assert r["ok"] is True
    assert len(r["question_ids"]) == 3
