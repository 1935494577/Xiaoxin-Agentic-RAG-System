"""TDD: exam paper export formats (markdown / docx / pdf)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _seed_paper(store, assemble):
    col = store.create_collection(name="导出库", subject="数学", grade="初二", region="浙江")
    for i in range(3):
        store.create_question(
            collection_id=col["id"],
            qtype="choice",
            difficulty=3,
            stem=f"选择题{i + 1}：下列正确的是？",
            options=["A. 1", "B. 2", "C. 3", "D. 4"],
            answer="A",
            analysis="解析",
            quality_status="published",
        )
    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="导出测试卷",
        spec={"by_qtype": {"choice": 2}, "seed": 1},
        include_answers=True,
    )
    assert r["ok"] is True
    return r


def test_export_formats_bytes(tmp_path, monkeypatch):
    from exam_bank import assemble, store
    from exam_bank.export_formats import EXPORT_FORMATS, export_paper_file

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    paper_res = _seed_paper(store, assemble)
    paper = store.get_paper(paper_res["paper_id"])
    assert paper is not None

    assert set(EXPORT_FORMATS) == {"markdown", "docx", "pdf"}

    md_bytes, md_ct, md_name = export_paper_file(paper, fmt="markdown")
    assert "导出测试卷".encode("utf-8") in md_bytes
    assert "markdown" in md_ct or md_ct.startswith("text/")
    assert md_name.endswith(".md")

    docx_bytes, docx_ct, docx_name = export_paper_file(paper, fmt="docx")
    assert len(docx_bytes) > 100
    assert docx_bytes[:2] == b"PK"  # zip/docx
    assert "officedocument" in docx_ct or docx_ct.endswith("document")
    assert docx_name.endswith(".docx")

    pdf_bytes, pdf_ct, pdf_name = export_paper_file(paper, fmt="pdf")
    assert pdf_bytes[:4] == b"%PDF"
    assert "pdf" in pdf_ct
    assert pdf_name.endswith(".pdf")


def test_export_invalid_format(tmp_path, monkeypatch):
    from exam_bank import assemble, store
    from exam_bank.export_formats import export_paper_file

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()
    paper_res = _seed_paper(store, assemble)
    paper = store.get_paper(paper_res["paper_id"])
    try:
        export_paper_file(paper, fmt="xlsx")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "unsupported" in str(e).lower() or "format" in str(e).lower()


def test_strip_export_noise_removes_jingyou():
    from exam_bank.export_rich import strip_export_noise

    raw = "二项式展开常数项是7．\n【考点】DA：二项式定理．菁优网版权所有\n【专题】35：转化思想．"
    cleaned = strip_export_noise(raw)
    assert "菁优网" not in cleaned
    assert "【考点】" not in cleaned
    assert "二项式" in cleaned


def test_export_pdf_embeds_eq_image(tmp_path, monkeypatch):
    """PDF must not leave raw [[EQ:n]]; embed formula PNG instead."""
    from PIL import Image

    from exam_bank import assemble, store
    from exam_bank.docx_extract import default_exam_media_root
    from exam_bank.export_formats import export_paper_file

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    media_root = tmp_path / "exam_media"
    monkeypatch.setattr(
        "exam_bank.docx_extract.default_exam_media_root",
        lambda: media_root,
    )
    # also patch export_rich resolver root via media in resolve using default_exam_media_root
    mid = "eqtest01"
    folder = media_root / mid
    folder.mkdir(parents=True)
    png = folder / "eq_7.png"
    Image.new("RGB", (40, 16), color=(0, 0, 0)).save(png)

    col = store.create_collection(name="公式导出库", subject="数学", grade="高三", region="浙江")
    q = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        difficulty=3,
        stem="已知向量[[EQ:7]]，则（ ）",
        options=["A. [[EQ:7]]", "B. 1", "C. 2", "D. 3"],
        answer="A",
        analysis="因为[[EQ:7]]，故选A。\n【考点】向量．菁优网版权所有",
        quality_status="published",
        media_ingest_id=mid,
    )
    r = assemble.assemble_paper(
        collection_id=col["id"],
        title="公式卷",
        spec={"by_qtype": {"choice": 1}, "seed": 1},
        include_answers=True,
    )
    assert r["ok"]
    paper = store.get_paper(r["paper_id"])
    pdf_bytes, _, _ = export_paper_file(paper, fmt="pdf")
    assert pdf_bytes[:4] == b"%PDF"
    # raw placeholder must not appear as plain text stream (latin-1 search)
    assert b"[[EQ:7]]" not in pdf_bytes
    assert b"/Image" in pdf_bytes or b"image" in pdf_bytes.lower()

    docx_bytes, _, _ = export_paper_file(paper, fmt="docx")
    assert docx_bytes[:2] == b"PK"
    assert b"[[EQ:7]]" not in docx_bytes
    # noise stripped from answers path — docx is zip; check via rebuild text helper
    from exam_bank.export_rich import sanitize_question_fields

    cleaned = sanitize_question_fields(q)
    assert "菁优网" not in cleaned["analysis"]
    assert "【考点】" not in cleaned["analysis"]
