"""TDD: PP-StructureV3 + LaTeXOCR paper parse → structured JSON."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_reorder_blocks_reading_order_and_latex():
    from exam_bank.paper_structure_parse import blocks_to_reading_text, normalize_structure_blocks

    raw = [
        {"type": "text", "content": "1. 已知", "page": 0, "order": 2, "bbox": [10, 80, 100, 100]},
        {"type": "formula", "content": "a\\in\\mathbb{R}", "page": 0, "order": 3, "bbox": [100, 80, 160, 100]},
        {"type": "text", "content": "，则（ ）", "page": 0, "order": 4, "bbox": [160, 80, 220, 100]},
        {"type": "text", "content": "标题", "page": 0, "order": 0, "bbox": [10, 10, 50, 30]},
    ]
    blocks = normalize_structure_blocks(raw)
    assert [b["content"] for b in blocks] == ["标题", "1. 已知", "a\\in\\mathbb{R}", "，则（ ）"]
    text = blocks_to_reading_text(blocks)
    assert "标题" in text
    assert "$a\\in\\mathbb{R}$" in text or "\\(a\\in\\mathbb{R}\\)" in text
    assert "1. 已知" in text


def test_parse_structure_result_dict_to_blocks():
    from exam_bank.paper_structure_parse import parsing_res_list_to_blocks

    page = {
        "page_index": 0,
        "parsing_res_list": [
            {
                "block_label": "text",
                "block_content": "选择题",
                "block_order": 0,
                "block_bbox": [0, 0, 10, 10],
            },
            {
                "block_label": "formula",
                "block_content": "x^2+1=0",
                "block_order": 1,
                "block_bbox": [0, 20, 40, 40],
            },
        ],
    }
    blocks = parsing_res_list_to_blocks(page)
    assert blocks[0]["type"] == "text"
    assert blocks[1]["type"] == "formula"
    assert blocks[1]["content"] == "x^2+1=0"


def _minimal_docx(tmp: Path) -> Path:
    docx = tmp / "paper.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>1. 已知集合 A，则（ ）</w:t></w:r></w:p>
    <w:p><w:r><w:t>A. 1</w:t></w:r></w:p>
    <w:p><w:r><w:t>B. 2</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        zf.writestr("word/document.xml", document_xml.encode("utf-8"))
        zf.writestr(
            "word/_rels/document.xml.rels",
            b'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
        )
    return docx


def test_docx_extract_path_without_paddle(tmp_path):
    from exam_bank.paper_structure_parse import parse_exam_paper

    path = _minimal_docx(tmp_path)
    with patch("exam_bank.paper_structure_parse.llm_structure_questions") as llm:
        llm.return_value = {
            "ok": True,
            "questions": [
                {
                    "question_no": "1",
                    "qtype": "choice",
                    "stem": "已知集合 A，则（ ）",
                    "options": ["A. 1", "B. 2"],
                    "answer": "",
                    "analysis": "",
                }
            ],
        }
        result = parse_exam_paper(path, use_llm=True)
    assert result["ok"] is True
    assert result["source_type"] == "docx"
    assert result["questions"]
    assert result["questions"][0]["question_no"] == "1"
    assert "已知集合" in (result.get("reading_order_text") or "")


def test_llm_structure_questions_parses_json():
    from exam_bank.paper_structure_parse import llm_structure_questions

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "questions": [
                                {
                                    "question_no": "1",
                                    "stem": "求 $x^2$",
                                    "options": ["A. 1"],
                                    "answer": "A",
                                    "analysis": "略",
                                    "qtype": "choice",
                                }
                            ]
                        },
                        ensure_ascii=False,
                    )
                )
            )
        ]
    )
    with patch(
        "exam_bank.llm_client.build_openai_client",
        return_value=(fake_client, {"chat_model": "deepseek-chat", "source": "test"}),
    ):
        out = llm_structure_questions("1. 求 $x^2$\nA. 1")
    assert out["ok"] is True
    assert out["questions"][0]["answer"] == "A"


def test_image_path_uses_ppstructure_when_available(tmp_path):
    from exam_bank.paper_structure_parse import parse_exam_paper

    img = tmp_path / "page.png"
    img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    class FakeRes:
        def __init__(self):
            self.json = {
                "page_index": 0,
                "parsing_res_list": [
                    {
                        "block_label": "text",
                        "block_content": "1. 已知函数",
                        "block_order": 0,
                        "block_bbox": [0, 0, 1, 1],
                    },
                    {
                        "block_label": "formula",
                        "block_content": "f(x)=x",
                        "block_order": 1,
                        "block_bbox": [0, 1, 1, 2],
                    },
                ],
            }

    fake_pipe = MagicMock()
    fake_pipe.predict.return_value = [FakeRes()]

    with (
        patch("exam_bank.paper_structure_parse.get_ppstructure_pipeline", return_value=fake_pipe),
        patch("exam_bank.paper_structure_parse.llm_structure_questions") as llm,
    ):
        llm.return_value = {
            "ok": True,
            "questions": [
                {
                    "question_no": "1",
                    "stem": "已知函数 $f(x)=x$",
                    "options": [],
                    "answer": "",
                    "analysis": "",
                    "qtype": "short",
                }
            ],
        }
        result = parse_exam_paper(img, use_llm=True)

    assert result["ok"] is True
    assert result["engine"] == "pp-structurev3"
    assert any(b["type"] == "formula" for b in result["blocks"])
    fake_pipe.predict.assert_called()


def test_structure_status_shape():
    from exam_bank.paper_structure_parse import structure_parse_status

    st = structure_parse_status()
    assert "available" in st
    assert "pp_structurev3" in st
    assert "hint" in st


def test_ppstructure_pipeline_disables_mkldnn():
    """Windows/CPU Paddle 3.3.x oneDNN+PIR crash → enable_mkldnn=False."""
    import exam_bank.paper_structure_parse as psp

    captured: dict = {}

    class FakePP:
        def __init__(self, **kw):
            captured.update(kw)

    fake_mod = MagicMock()
    fake_mod.PPStructureV3 = FakePP
    with patch.dict("sys.modules", {"paddleocr": fake_mod}):
        pipe = psp.get_ppstructure_pipeline(force_reload=True)
    assert pipe is not None
    assert captured.get("enable_mkldnn") is False
    assert captured.get("use_formula_recognition") is True
    psp._pipeline = None
    psp._pipeline_error = ""
