"""TDD: search source papers for chat exam retrieval."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_search_source_papers_by_title(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    col = store.create_collection(
        name="浙江·数学·高三", subject="数学", grade="高三", region="浙江"
    )
    sp1 = store.create_source_paper(
        collection_id=col["id"],
        title="2024年高考数学新课标I卷",
        source_filename="2024_math_i.docx",
    )
    store.create_source_paper(
        collection_id=col["id"],
        title="2023年高考数学新课标I卷",
        source_filename="2023_math_i.docx",
    )
    store.create_source_paper(
        collection_id=col["id"],
        title="期末练习卷",
        source_filename="midterm.pdf",
    )

    hits = store.search_source_papers("2024 新课标")
    assert len(hits) >= 1
    assert hits[0]["id"] == sp1["id"]
    assert hits[0]["title"] == "2024年高考数学新课标I卷"

    by_file = store.search_source_papers("midterm")
    assert len(by_file) == 1
    assert "期末" in by_file[0]["title"]

    empty = store.search_source_papers("不存在的卷名xyz")
    assert empty == []


def test_search_source_papers_respects_limit_and_collection(tmp_path, monkeypatch):
    from exam_bank import store

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    col_a = store.create_collection(name="A", subject="数学", grade="高三", region="浙江")
    col_b = store.create_collection(name="B", subject="语文", grade="高三", region="浙江")
    store.create_source_paper(collection_id=col_a["id"], title="模拟卷甲")
    store.create_source_paper(collection_id=col_a["id"], title="模拟卷乙")
    store.create_source_paper(collection_id=col_b["id"], title="模拟卷丙语文")

    all_hits = store.search_source_papers("模拟卷", limit=10)
    assert len(all_hits) == 3
    limited = store.search_source_papers("模拟卷", limit=2)
    assert len(limited) == 2
    only_a = store.search_source_papers("模拟卷", collection_id=col_a["id"])
    assert len(only_a) == 2
    assert all(h["collection_id"] == col_a["id"] for h in only_a)
