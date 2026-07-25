"""TDD: formal exam paper layout."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_render_formal_markdown_looks_like_exam():
    from exam_bank.paper_layout import render_formal_markdown

    qs = [
        {
            "qtype": "choice",
            "stem": "已知集合 A={1}，则 ( )",
            "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
            "answer": "A",
            "analysis": "直接观察",
        },
        {
            "qtype": "choice",
            "stem": "第二题 ( )",
            "options": ["A. 甲", "B. 乙"],
            "answer": "B",
            "analysis": "",
        },
        {
            "qtype": "fill",
            "stem": "1+1=____",
            "options": [],
            "answer": "2",
            "analysis": "",
        },
    ]
    md = render_formal_markdown(
        title="2024年高考数学模拟卷",
        questions=qs,
        include_answers=True,
        subtitle="满分 150 分　考试时间 120 分钟",
    )
    assert "2024年高考数学模拟卷" in md
    assert "姓名__________" in md
    assert "一、选择题（本大题共 2 小题）" in md
    assert "二、填空题（本大题共 1 小题）" in md
    assert "1. 已知集合" in md
    assert "　　A. 1" in md or "A. 1" in md
    assert "参考答案与解析" in md
    assert "【答案】A" in md
    assert "# " not in md.split("\n")[0]  # not blog H1
