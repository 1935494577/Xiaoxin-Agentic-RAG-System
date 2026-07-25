"""TDD: corpus path metadata inference."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_infer_gaokao_path():
    from exam_bank.corpus_meta import infer_corpus_meta

    p = Path(r"d:/试卷资料/试卷资料/2024/高中/高三/数学/浙江/2024年高考数学试卷（新课标Ⅰ卷）（解析）.docx")
    root = Path(r"d:/试卷资料/试卷资料")
    m = infer_corpus_meta(p, root=root)
    assert m["year"] == "2024"
    assert m["subject"] == "数学"
    assert m["region"] == "浙江"
    assert m["grade"] == "高三"
    assert m["exam_type"] == "高考"
    assert m["paper_kind"] == "answer"


def test_infer_weekly_guangdong():
    from exam_bank.corpus_meta import infer_corpus_meta

    p = Path(
        r"d:/试卷资料/试卷资料/2026/高中/高一/数学/广东/广东省佛山市高中某校周测.docx"
    )
    m = infer_corpus_meta(p, root=Path(r"d:/试卷资料/试卷资料"))
    assert m["grade"] == "高一"
    assert m["region"] == "广东"
    assert m["subject"] == "数学"


def test_rank_prefers_answer_docx():
    from exam_bank.corpus_meta import rank_paper_candidate

    a = {"paper_kind": "answer", "layout": "A4"}
    b = {"paper_kind": "blank", "layout": "A4"}
    assert rank_paper_candidate(a, Path("a.docx")) > rank_paper_candidate(b, Path("b.docx"))
    assert rank_paper_candidate(a, Path("a.docx")) > rank_paper_candidate(a, Path("a.pdf"))
    assert rank_paper_candidate(a, Path("a.pdf")) > rank_paper_candidate(a, Path("a.doc"))
