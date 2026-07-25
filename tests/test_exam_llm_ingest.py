"""TDD: LLM-first exam paper item extraction (filter junk, qtypes, answers, tags)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


SAMPLE_WITH_JUNK = """
2024年高考数学试卷（新课标Ⅰ卷）
注意事项：
1. 答题前填写姓名、准考证号
2. 选择题用2B铅笔填涂
一、选择题
1. 已知集合 A={1,2}，则 ( )
A. 1
B. 2
C. 3
D. 4
【答案】A
【解析】直接观察。
2. 函数 f(x)=x 的值域是 ( )
A. R
B. [0,+∞)
C. (0,+∞)
D. {0}
【答案】A
二、填空题
3. 1+1=____
【答案】2
"""


def test_normalize_llm_items_filters_junk_and_keeps_answers():
    from exam_bank.llm_ingest import normalize_llm_items

    raw = [
        {
            "question_no": "1",
            "qtype": "choice",
            "stem": "已知集合 A={1,2}，则 ( )",
            "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
            "answer": "A",
            "analysis": "直接观察。",
            "knowledge_tags": ["集合"],
            "difficulty": 2,
            "is_question": True,
        },
        {
            "question_no": "",
            "qtype": "other",
            "stem": "答题前填写姓名、准考证号",
            "options": [],
            "answer": "",
            "is_question": False,
        },
        {
            "question_no": "3",
            "qtype": "fill",
            "stem": "1+1=____",
            "options": [],
            "answer": "2",
            "knowledge_tags": ["运算"],
            "difficulty": 1,
            "is_question": True,
        },
    ]
    items, meta = normalize_llm_items(raw, subject="数学", grade="高三")
    assert len(items) == 2
    assert items[0]["qtype"] == "choice"
    assert items[0]["answer"] == "A"
    assert items[0]["difficulty"] == 2
    assert "集合" in items[0]["knowledge_tags"]
    assert items[1]["qtype"] == "fill"
    assert items[1]["difficulty"] == 1
    assert meta["answers_embedded"] is True
    assert meta["skipped_non_questions"] == 1


def test_parse_paper_items_prefers_llm(monkeypatch):
    from exam_bank import item_split, llm_ingest

    def fake_extract(text, **kwargs):
        del text, kwargs
        return {
            "items": [
                {
                    "question_no": "1",
                    "qtype": "choice",
                    "stem": "题干",
                    "options": ["A. 1"],
                    "answer": "A",
                    "analysis": "",
                    "knowledge_tags": ["代数"],
                    "selected": True,
                }
            ],
            "answers_embedded": True,
            "skipped_non_questions": 2,
            "router": "llm_items",
            "model": "mock",
        }

    monkeypatch.setattr(llm_ingest, "extract_items_with_llm", fake_extract)
    out = item_split.parse_paper_items(
        SAMPLE_WITH_JUNK,
        subject="数学",
        grade="高三",
        region="浙江",
        use_llm=True,
    )
    assert out["router"] == "llm_items"
    assert out["answers_embedded"] is True
    assert out["item_count"] == 1
    assert out["items"][0]["answer"] == "A"
    assert "代数" in out["items"][0]["knowledge_tags"]


def test_parse_paper_items_rules_fallback_when_llm_off():
    from exam_bank.item_split import parse_paper_items

    out = parse_paper_items(
        "一、选择题\n1. 已知集合 A，则 ( )\nA. 1\nB. 2\n",
        subject="数学",
        grade="高三",
        use_llm=False,
    )
    assert out["router"] == "rules"
    assert out["item_count"] >= 1


def test_parse_paper_items_llm_fail_does_not_dump_junk(monkeypatch):
    from exam_bank import item_split, llm_ingest

    monkeypatch.setattr(llm_ingest, "extract_items_with_llm", lambda *a, **k: None)
    junk = """注意事项：
1. 答题前填写姓名、准考证号
2. 选择题用2B铅笔填涂
一、选择题
3. 已知集合，则 ( )
A. 1
B. 2
"""
    out = item_split.parse_paper_items(junk, subject="数学", grade="高三", use_llm=True)
    assert out["router"] == "llm_failed"
    assert out["item_count"] == 0
    assert out.get("error") == "llm_extract_failed"
