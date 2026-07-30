"""TDD: question completeness flags for manage/assemble closed loop."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_choice_with_letter_only_options_is_incomplete():
    from exam_bank.question_quality import is_question_incomplete, incomplete_reasons

    q = {
        "qtype": "choice",
        "stem": "函数y=sin2x的图像是()",
        "options": ["A", "B", "C", "D"],
        "answer": "",
        "analysis": "",
    }
    assert is_question_incomplete(q) is True
    reasons = incomplete_reasons(q)
    assert "options" in reasons
    assert "answer" in reasons


def test_choice_with_full_options_and_answer_is_complete():
    from exam_bank.question_quality import is_question_incomplete

    q = {
        "qtype": "choice",
        "stem": "1+1=?",
        "options": ["A. 1", "B. 2", "C. 3", "D. 4"],
        "answer": "B",
        "analysis": "显然",
    }
    assert is_question_incomplete(q) is False


def test_short_answer_missing_answer_is_incomplete():
    from exam_bank.question_quality import is_question_incomplete, incomplete_reasons

    q = {
        "qtype": "short",
        "stem": "证明勾股定理",
        "options": [],
        "answer": "",
        "analysis": "",
    }
    assert is_question_incomplete(q) is True
    assert "answer" in incomplete_reasons(q)


def test_annotate_completeness_adds_fields():
    from exam_bank.question_quality import annotate_completeness

    out = annotate_completeness(
        {
            "id": "1",
            "qtype": "choice",
            "stem": "x",
            "options": ["A."],
            "answer": "",
            "analysis": "",
        }
    )
    assert out["incomplete"] is True
    assert isinstance(out["incomplete_reasons"], list)
    assert out["incomplete_reasons"]
