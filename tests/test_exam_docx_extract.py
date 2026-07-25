"""TDD: DOCX extract keeps MathType/OLE as [[EQ:n]] placeholders."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _minimal_docx_with_ole(tmp: Path) -> Path:
    """Build a tiny docx: text + fake OLE image relationship."""
    docx = tmp / "sample.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:v="urn:schemas-microsoft-com:vml">
  <w:body>
    <w:p>
      <w:r><w:t>1. 已知集合</w:t></w:r>
      <w:r>
        <w:object>
          <v:shape>
            <v:imagedata r:id="rId9"/>
          </v:shape>
        </w:object>
      </w:r>
      <w:r><w:t>，则（    ）</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId9"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
    Target="media/image1.wmf"/>
</Relationships>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="wmf" ContentType="image/x-wmf"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        zf.writestr("word/document.xml", document_xml.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", rels_xml.encode("utf-8"))
        zf.writestr("word/media/image1.wmf", b"fake-wmf-bytes")
    return docx


def test_extract_docx_inserts_eq_placeholder(tmp_path):
    from exam_bank.docx_extract import extract_docx_exam

    path = _minimal_docx_with_ole(tmp_path)
    media_dir = tmp_path / "media"
    result = extract_docx_exam(path, media_dir=media_dir)
    assert "[[EQ:1]]" in result["text"]
    assert "已知集合" in result["text"]
    assert result["eq_count"] >= 1
    assert result["media"]
    saved = Path(result["media"][0]["path"])
    assert saved.is_file()


def _docx_with_preview_and_ole(tmp: Path) -> Path:
    """MathType-style object: VML preview image + OLE .bin (must become ONE placeholder)."""
    docx = tmp / "preview_ole.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:o="urn:schemas-microsoft-com:office:office">
  <w:body>
    <w:p>
      <w:r><w:t>选项 A </w:t></w:r>
      <w:r>
        <w:object>
          <v:shape>
            <v:imagedata r:id="rIdImg"/>
          </v:shape>
          <o:OLEObject r:id="rIdOle"/>
        </w:object>
      </w:r>
    </w:p>
  </w:body>
</w:document>
"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdImg"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
    Target="media/image1.wmf"/>
  <Relationship Id="rIdOle"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject"
    Target="embeddings/oleObject1.bin"/>
</Relationships>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="wmf" ContentType="image/x-wmf"/>
  <Default Extension="bin" ContentType="application/vnd.openxmlformats-officedocument.oleObject"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        zf.writestr("word/document.xml", document_xml.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", rels_xml.encode("utf-8"))
        zf.writestr("word/media/image1.wmf", b"fake-wmf-bytes")
        zf.writestr("word/embeddings/oleObject1.bin", b"fake-ole-bytes")
    return docx


def test_extract_prefers_preview_image_over_ole(tmp_path):
    from exam_bank.docx_extract import extract_docx_exam, resolve_eq_media_file

    path = _docx_with_preview_and_ole(tmp_path)
    media_dir = tmp_path / "media"
    result = extract_docx_exam(path, media_dir=media_dir)
    assert result["text"].count("[[EQ:") == 1
    assert "[[EQ:1]]" in result["text"]
    assert result["eq_count"] == 1
    assert len(result["media"]) == 1
    saved = Path(result["media"][0]["path"])
    assert saved.is_file()
    assert "ole" not in saved.name.lower()
    assert saved.suffix.lower() in {".wmf", ".png", ".emf"}
    resolved = resolve_eq_media_file(media_dir, result["ingest_id"], 1)
    assert resolved is not None
    assert resolved.suffix.lower() != ".bin"


def test_resolve_eq_skips_ole_bin(tmp_path):
    from exam_bank.docx_extract import resolve_eq_media_file

    folder = tmp_path / "ing1"
    folder.mkdir()
    (folder / "eq_9_oleObject1.bin").write_bytes(b"ole")
    assert resolve_eq_media_file(tmp_path, "ing1", 9) is None
    (folder / "eq_9.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    assert resolve_eq_media_file(tmp_path, "ing1", 9).name == "eq_9.png"
