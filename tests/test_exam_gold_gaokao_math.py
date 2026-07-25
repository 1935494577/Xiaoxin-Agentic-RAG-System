"""Gold-standard: 2024 新课标Ⅰ 数学 blank/answer fixtures → 19 items, options, embedded answers."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "exam_papers"


def test_gold_2024_blank_19_questions():
    from exam_bank.item_split import parse_paper_items

    raw = FIXTURES.joinpath("2024_blank_0.txt").read_text(encoding="utf-8")
    result = parse_paper_items(raw, subject="数学", grade="高三", region="浙江", use_llm=False)
    items = result["items"]
    assert result.get("clean_applied") is True
    assert len(items) == 19
    nos = [it["question_no"] for it in items]
    assert nos == [str(i) for i in range(1, 20)]
    # choice 1-8 single, 9-11 multi-like, fill 12-14, essay 15-19
    for it in items[:8]:
        assert it["qtype"] in {"choice", "multi"}
        assert len(it["options"]) == 4, f"q{it['question_no']} opts={it['options']}"
    for it in items[8:11]:
        assert len(it["options"]) == 4
    for it in items[11:14]:
        assert it["qtype"] == "fill"
        assert it["options"] == []
    for it in items[14:]:
        assert it["qtype"] in {"short", "calc", "other"}
        # sub-questions stay in stem
        assert "(1)" in it["stem"] or "（1）" in it["stem"] or it["question_no"] == "19"


def test_gold_2024_answer_embedded():
    from exam_bank.item_split import parse_paper_items

    raw = FIXTURES.joinpath("2024_answer_1.txt").read_text(encoding="utf-8")
    result = parse_paper_items(raw, subject="数学", grade="高三", use_llm=False)
    items = result["items"]
    assert len(items) == 19
    assert result.get("answers_embedded") is True
    # early choice answers
    by_no = {it["question_no"]: it for it in items}
    assert by_no["1"]["answer"].strip() in {"A", "A."} or by_no["1"]["answer"].startswith("A")
    assert "解析" in by_no["1"]["analysis"] or len(by_no["1"]["analysis"]) > 5
    assert by_no["9"]["answer"].replace(" ", "") in {"BC", "B.C", "B、C"} or "B" in by_no["9"]["answer"]
