"""TDD: exam-bank OCR ingest (PaddleOCR optional, no CamScanner)."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_ocr_status_reports_missing_when_engines_absent(monkeypatch):
    from exam_bank import ocr_ingest

    monkeypatch.setattr(ocr_ingest, "_try_import_paddle", lambda: (None, "paddleocr not installed"))
    monkeypatch.setattr(ocr_ingest, "_try_import_pdfium", lambda: (None, "pypdfium2 not installed"))
    monkeypatch.setattr(ocr_ingest, "_try_import_fitz", lambda: (None, "pymupdf not installed"))
    # PPStructureV3 probe happens via import inside ocr_status — patch builtins if needed
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "paddleocr" or name.startswith("paddleocr."):
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    st = ocr_ingest.ocr_status()
    assert st["available"] is False
    assert "paddleocr" in st["missing"]
    assert st["pdf_render_ready"] is False


def test_lines_from_paddle_result_sorted_reading_order():
    from exam_bank.ocr_ingest import lines_from_paddle_page

    # two columns: left then right should become left-first by y/x sort
    page = [
        [[[200, 10], [280, 10], [280, 30], [200, 30]], ("右栏标题", 0.99)],
        [[[10, 10], [80, 10], [80, 30], [10, 30]], ("左栏标题", 0.98)],
        [[[10, 40], [90, 40], [90, 60], [10, 60]], ("左栏正文", 0.97)],
    ]
    text = lines_from_paddle_page(page)
    assert "左栏标题" in text.splitlines()[0]
    assert "右栏标题" in text
    assert text.index("左栏标题") < text.index("右栏标题")


def test_ocr_image_bytes_uses_engine(monkeypatch):
    from exam_bank import ocr_ingest

    class FakeEngine:
        name = "paddleocr"

        def recognize(self, path: str):
            return [
                [[[0, 0], [10, 0], [10, 10], [0, 10]], ("第一部分 听力", 0.9)],
                [[[0, 20], [10, 20], [10, 30], [0, 30]], ("1. What will they do?", 0.9)],
            ]

    monkeypatch.setattr(ocr_ingest, "get_ocr_engine", lambda: FakeEngine())
    out = ocr_ingest.ocr_image_bytes(b"fake-png-bytes", filename="page.png")
    assert "第一部分 听力" in out["text"]
    assert out["page_count"] == 1
    assert out["engine"] == "paddleocr"


def test_ocr_pdf_renders_pages(monkeypatch, tmp_path):
    from exam_bank import ocr_ingest

    calls: list[int] = []

    def fake_render(path, *, max_pages=30, dpi=150):
        calls.append(1)
        return [b"page0", b"page1"]

    class FakeEngine:
        name = "paddleocr"

        def __init__(self) -> None:
            self.n = 0

        def recognize(self, path: str):
            tag = f"page{self.n}"
            self.n += 1
            return [[[[0, 0], [1, 0], [1, 1], [0, 1]], (tag, 0.9)]]

    monkeypatch.setattr(ocr_ingest, "render_pdf_page_images", fake_render)
    engine = FakeEngine()
    monkeypatch.setattr(ocr_ingest, "get_ocr_engine", lambda: engine)
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    out = ocr_ingest.ocr_file(pdf)
    assert calls == [1]
    assert "page0" in out["text"] and "page1" in out["text"]
    assert out["page_count"] == 2


def test_ingest_ocr_api_503_when_unavailable(monkeypatch, tmp_path):
    from exam_bank import ocr_ingest, store

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "ocr.db")
    store.init_exam_bank_db()
    monkeypatch.setattr(
        ocr_ingest,
        "ocr_status",
        lambda: {
            "available": False,
            "missing": ["paddleocr"],
            "hint": "pip install -r requirements-exam-optional.txt",
        },
    )
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        r = client.get("/api/exam/ingest/ocr/status")
        assert r.status_code == 200
        assert r.json()["available"] is False

        files = {"file": ("scan.png", b"\x89PNG\r\n", "image/png")}
        r2 = client.post("/api/exam/ingest/ocr", files=files, data={"use_llm": "false"})
        assert r2.status_code == 503
        assert "ocr" in r2.json()["detail"].lower()


def test_ingest_ocr_api_success_mocked(monkeypatch, tmp_path):
    from exam_bank import ocr_ingest, store

    monkeypatch.setattr(store.settings, "exam_bank_db_path", tmp_path / "ocr2.db")
    store.init_exam_bank_db()
    monkeypatch.setattr(
        ocr_ingest,
        "ocr_status",
        lambda: {"available": True, "missing": [], "engines": ["paddleocr"]},
    )
    monkeypatch.setattr(
        ocr_ingest,
        "ocr_file",
        lambda path, **kw: {
            "text": "第一部分 听力\n1. What will they do?\nA. Pack\nB. Go\nC. Stay\n",
            "page_count": 1,
            "engine": "paddleocr",
            "warnings": [],
        },
    )
    from api.exam_router import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        files = {"file": ("scan.png", b"\x89PNG\r\n", "image/png")}
        r = client.post(
            "/api/exam/ingest/ocr",
            files=files,
            data={"subject": "英语", "grade": "高三", "use_llm": "false", "clean": "true"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ocr_applied") is True
        assert "听力" in (body.get("raw_text") or "")
        assert body.get("item_count", 0) >= 1
        assert any(it.get("qtype") == "listening" for it in body.get("items") or [])
