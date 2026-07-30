"""TDD: exam paper cleaning for gaokao-style fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "exam_papers"


def test_strip_notice_and_keep_sections():
    from exam_bank.paper_clean import clean_exam_paper

    raw = FIXTURES.joinpath("2024_blank_0.txt").read_text(encoding="utf-8")
    result = clean_exam_paper(raw)
    cleaned = result["cleaned"]
    assert "注意事项" not in cleaned
    assert "答题前" not in cleaned
    assert "一、选择题" in cleaned
    assert "四、解答题" in cleaned
    assert "绝密" not in cleaned.splitlines()[0]
    assert any("stripped_notice" in w for w in result["warnings"])


def test_split_inline_options():
    from exam_bank.paper_clean import clean_exam_paper, split_inline_options_line

    assert split_inline_options_line("A. 3B. 4C. 6D. 8") == [
        "A. 3",
        "B. 4",
        "C. 6",
        "D. 8",
    ]
    raw = "7. 交点个数为（    ）\nA. 3B. 4C. 6D. 8\n"
    cleaned = clean_exam_paper(raw)["cleaned"]
    assert "A. 3" in cleaned.splitlines()
    assert "D. 8" in cleaned.splitlines()


def test_preserve_eq_placeholders():
    from exam_bank.paper_clean import clean_exam_paper

    raw = "注意事项：\n1. 答题前填写姓名\n一、选择题\n1. 已知[[EQ:1]]，则（    ）\nA. [[EQ:2]]B. [[EQ:3]]C. [[EQ:4]]D. [[EQ:5]]\n"
    cleaned = clean_exam_paper(raw)["cleaned"]
    assert "[[EQ:1]]" in cleaned
    assert "注意事项" not in cleaned
    lines = cleaned.splitlines()
    assert any(ln.startswith("A. ") and "[[EQ:2]]" in ln for ln in lines)


def test_collapse_pdf_spaced_cjk():
    from exam_bank.paper_clean import clean_exam_paper, collapse_spaced_cjk

    raw = "【 详 解 】可 知 k         AC: y  1"
    assert collapse_spaced_cjk(raw) == "【详解】可知 k AC: y 1"
    assert "[[EQ:12]]" in collapse_spaced_cjk("已 知[[EQ:12]]，则")
    cleaned = clean_exam_paper("一、选择题\n1. 【 答 案 】A\n")["cleaned"]
    assert "【答案】" in cleaned
    assert "【 答" not in cleaned
