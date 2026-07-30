"""TDD: subject × stage catalog + LLM paper router (mocked)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_math_junior_is_choice_fill_short():
    from exam_bank.subject_catalog import qtypes_for_subject

    qts = qtypes_for_subject("数学", grade="初二")
    assert qts == ["choice", "fill", "short"]
    assert "big" not in qts
    assert "calc" not in qts


def test_english_junior_has_cloze_reading():
    from exam_bank.subject_catalog import qtypes_for_subject

    qts = qtypes_for_subject("英语", stage="junior")
    assert "cloze" in qts
    assert "reading" in qts
    assert "listening" in qts


def test_history_material():
    from exam_bank.subject_catalog import qtypes_for_subject, qtype_label

    qts = qtypes_for_subject("历史", stage="senior")
    assert "material" in qts
    assert qtype_label("material") == "材料分析题"


def test_analyze_paper_llm_mocked(monkeypatch):
    from exam_bank import paper_router

    def fake_llm(text, **kwargs):
        return {
            "subject": "数学",
            "grade": "初二",
            "stage": "junior",
            "sections": [
                {"heading": "一、选择题", "qtype": "choice", "approx_count": 10},
                {"heading": "二、填空题", "qtype": "fill", "approx_count": 6},
                {"heading": "三、解答题", "qtype": "short", "approx_count": 6},
            ],
            "confidence": 0.9,
            "router": "llm",
        }

    monkeypatch.setattr(paper_router, "route_paper_with_llm", fake_llm)
    out = paper_router.analyze_paper("任意", subject="", grade="", use_llm=True)
    assert out["router"] == "llm"
    assert out["subject"] == "数学"
    assert [s["qtype"] for s in out["sections"]][:3] == ["choice", "fill", "short"]
    assert out["suggested_qtypes"]


def test_analyze_paper_fallback_rules(monkeypatch):
    from exam_bank import paper_router

    monkeypatch.setattr(paper_router, "route_paper_with_llm", lambda *a, **k: None)
    text = "一、选择题\n1.x\n二、填空题\n2.y\n三、解答题\n3.z"
    out = paper_router.analyze_paper(text, subject="数学", grade="初二", use_llm=True)
    assert out["router"] == "rules"
    assert "llm_unavailable" in out.get("note", "")
    ids = [s["qtype"] for s in out["sections"]]
    assert "choice" in ids and "fill" in ids
