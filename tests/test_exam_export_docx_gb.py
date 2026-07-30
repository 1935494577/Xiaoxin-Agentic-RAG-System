"""TDD: GB/T-style Word exam export (margins, lists, options table, LaTeX→OMML)."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_latex_to_omml_element_is_omath():
    from exam_bank.export_docx_gb import latex_to_omml_element

    el = latex_to_omml_element(r"\frac{1}{2}")
    assert el is not None
    assert "oMath" in el.tag


def test_build_gb_docx_margins_a4_and_omml(tmp_path):
    from docx import Document
    from docx.shared import Cm, Mm

    from exam_bank.export_docx_gb import build_gb_docx_bytes

    questions = [
        {
            "qtype": "choice",
            "stem": "已知 $a\\in\\mathbb{R}$，则（ ）",
            "options": ["A. $1$", "B. $2$", "C. $3$", "D. $4$"],
            "answer": "A",
            "analysis": "因为 $\\frac{1}{2}$",
            "media_ingest_id": "",
        },
        {
            "qtype": "short",
            "stem": "求证：（1）$x>0$；（2）$y<1$",
            "options": [],
            "answer": "略",
            "analysis": "",
            "media_ingest_id": "",
        },
    ]
    raw = build_gb_docx_bytes(
        title="国标排版测试卷",
        questions=questions,
        include_answers=True,
    )
    assert raw[:2] == b"PK"
    path = tmp_path / "gb.docx"
    path.write_bytes(raw)
    doc = Document(str(path))
    sec = doc.sections[0]
    # A4 width ≈ 210mm
    assert abs(float(sec.page_width) - float(Mm(210))) < float(Mm(1))
    for m in (sec.top_margin, sec.bottom_margin, sec.left_margin, sec.right_margin):
        assert abs(float(m) - float(Cm(2.54))) < float(Cm(0.05))

    # numbering definitions present
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        assert "word/numbering.xml" in names
        numbering = zf.read("word/numbering.xml").decode("utf-8")
        assert "abstractNum" in numbering
        # OMML math present
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        assert "oMath" in doc_xml
        assert "tbl" in doc_xml  # options as borderless table


def test_split_rich_segments_latex_and_eq():
    from exam_bank.export_docx_gb import split_rich_segments

    segs = split_rich_segments("前$\\frac{1}{2}$后[[EQ:3]]尾")
    kinds = [s[0] for s in segs]
    assert "latex" in kinds
    assert "eq" in kinds
    assert "text" in kinds
