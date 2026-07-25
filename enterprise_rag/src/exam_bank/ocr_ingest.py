"""Optional OCR preprocess for scanned exam papers.

Preferred stack（提示词对齐）::
    pip install -r requirements-exam-optional.txt
    # + paddlepaddle from https://www.paddlepaddle.org.cn/packages/stable/cpu/

Uses **PaddleOCR** (PP-OCRv / structure 同源). PDF 渲页：**pypdfium2**（或 pymupdf）。
版面+公式请用 ``exam_bank.paper_structure_parse``（PP-StructureV3 + LaTeX_OCR_rec）。

Does not require CamScanner — upload PDF/PNG/JPG to ``POST /api/exam/ingest/ocr``.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
_PDF_SUFFIXES = {".pdf"}

_ocr_engine: Any = None
_ocr_engine_error: str | None = None
_ocr_engine_name: str = ""


def _try_import_paddle() -> tuple[Any, str | None]:
    try:
        from paddleocr import PaddleOCR  # type: ignore

        return PaddleOCR, None
    except Exception as e:  # noqa: BLE001
        return None, f"paddleocr not available: {e}"


def _try_import_pdfium() -> tuple[Any, str | None]:
    try:
        import pypdfium2 as pdfium  # type: ignore

        return pdfium, None
    except Exception as e:  # noqa: BLE001
        return None, f"pypdfium2 not installed: {e}"


def _try_import_fitz() -> tuple[Any, str | None]:
    try:
        import fitz  # pymupdf

        return fitz, None
    except Exception as e:  # noqa: BLE001
        return None, f"pymupdf not installed: {e}"


def ocr_status() -> dict[str, Any]:
    """Whether OCR deps are importable (does not load models yet)."""
    missing: list[str] = []
    engines: list[str] = []
    _, paddle_err = _try_import_paddle()
    if not paddle_err:
        engines.append("paddleocr")
    else:
        missing.append("paddleocr")

    try:
        from paddleocr import PPStructureV3  # type: ignore  # noqa: F401

        engines.append("pp-structurev3")
    except Exception:
        missing.append("paddleocr[doc-parser]/PPStructureV3")

    pdfium, _ = _try_import_pdfium()
    fitz, fitz_err = _try_import_fitz()
    if pdfium is not None:
        engines.append("pypdfium2")
    elif fitz is not None:
        engines.append("pymupdf")
    else:
        missing.append("pypdfium2")
        if fitz_err:
            missing.append("pymupdf")

    available = "paddleocr" in engines or "pp-structurev3" in engines
    hint = ""
    if not available:
        hint = (
            "pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ ; "
            'pip install "paddleocr[doc-parser]>=3.0" -r requirements-exam-optional.txt'
        )
    return {
        "available": available,
        "missing": missing,
        "engines": engines,
        "hint": hint,
        "supported_suffixes": sorted(_IMAGE_SUFFIXES | _PDF_SUFFIXES),
        "pdf_render_ready": pdfium is not None or fitz is not None,
        "structure_parse": "exam_bank.paper_structure_parse",
    }


class _PaddleEngine:
    name = "paddleocr"

    def __init__(self, cls: Any) -> None:
        # disable oneDNN: Paddle 3.3.x PIR + mkldnn crashes on Windows CPU
        attempts: list[dict[str, Any]] = [
            {"use_angle_cls": True, "lang": "ch", "show_log": False, "enable_mkldnn": False},
            {"lang": "ch", "enable_mkldnn": False},
            {"lang": "ch"},
            {},
        ]
        last: Exception | None = None
        for kw in attempts:
            try:
                self._eng = cls(**kw)
                return
            except TypeError as e:
                last = e
                continue
        if last is not None:
            raise last
        self._eng = cls()

    def recognize(self, path: str) -> list:
        try:
            raw = self._eng.ocr(path, cls=True)
        except TypeError:
            raw = self._eng.ocr(path)
        if raw is None:
            return []
        if isinstance(raw, list) and raw and raw[0] is not None and len(raw[0]) >= 2 and not isinstance(
            raw[0][0], (list, tuple)
        ):
            return list(raw)
        pages = list(raw or [])
        if not pages:
            return []
        return list(pages[0] or [])


def get_ocr_engine() -> Any:
    """Lazy singleton: PaddleOCR."""
    global _ocr_engine, _ocr_engine_error, _ocr_engine_name
    if _ocr_engine is not None:
        return _ocr_engine
    if _ocr_engine_error:
        raise RuntimeError(_ocr_engine_error)

    paddle_cls, paddle_err = _try_import_paddle()
    if paddle_cls is not None:
        _ocr_engine = _PaddleEngine(paddle_cls)
        _ocr_engine_name = "paddleocr"
        return _ocr_engine

    _ocr_engine_error = paddle_err or "no OCR engine (install paddleocr[doc-parser])"
    raise RuntimeError(_ocr_engine_error)


def _box_sort_key(box: list) -> tuple[int, int]:
    try:
        ys = [float(p[1]) for p in box]
        xs = [float(p[0]) for p in box]
        y = int(sum(ys) / max(len(ys), 1))
        x = int(min(xs) if xs else 0)
        return (y // 18, x)
    except Exception:  # noqa: BLE001
        return (0, 0)


def lines_from_paddle_page(page_result: list | None) -> str:
    """Flatten one page of [box, (text, conf)] into reading-order text."""
    if not page_result:
        return ""
    rows: list[tuple[tuple[int, int], str]] = []
    for item in page_result:
        if not item or len(item) < 2:
            continue
        box, payload = item[0], item[1]
        text = ""
        if isinstance(payload, (list, tuple)) and payload:
            text = str(payload[0] or "").strip()
        elif isinstance(payload, str):
            text = payload.strip()
        if not text:
            continue
        rows.append((_box_sort_key(box), text))
    rows.sort(key=lambda r: r[0])
    return "\n".join(t for _, t in rows)


def ocr_image_bytes(
    data: bytes,
    *,
    filename: str = "page.png",
) -> dict[str, Any]:
    """OCR a single image (PNG/JPEG bytes)."""
    del filename
    if not data:
        return {"text": "", "page_count": 0, "engine": _ocr_engine_name or "none", "warnings": ["empty_image"]}
    engine = get_ocr_engine()
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(data)
        path = tmp.name
    warnings: list[str] = []
    try:
        page_lines = engine.recognize(path)
    finally:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    text = lines_from_paddle_page(page_lines)
    if not text.strip():
        warnings.append("ocr_empty_result")
    return {
        "text": text,
        "page_count": 1,
        "engine": getattr(engine, "name", _ocr_engine_name or "ocr"),
        "warnings": warnings,
    }


def render_pdf_page_images(
    path: Path,
    *,
    max_pages: int = 40,
    dpi: int = 160,
) -> list[bytes]:
    """Rasterize PDF pages (pypdfium2 preferred, pymupdf fallback)."""
    pdfium, _ = _try_import_pdfium()
    if pdfium is not None:
        return _render_pdf_pdfium(path, pdfium, max_pages=max_pages, dpi=dpi)
    fitz, err = _try_import_fitz()
    if err or fitz is None:
        raise RuntimeError(
            "pypdfium2 (or pymupdf) required to OCR PDF pages; "
            "pip install -r requirements-exam-optional.txt"
        )
    return _render_pdf_fitz(path, fitz, max_pages=max_pages, dpi=dpi)


def _render_pdf_pdfium(
    path: Path,
    pdfium: Any,
    *,
    max_pages: int,
    dpi: int,
) -> list[bytes]:
    doc = pdfium.PdfDocument(str(path))
    try:
        n = min(len(doc), max(1, int(max_pages)))
        scale = max(1.0, float(dpi) / 72.0)
        out: list[bytes] = []
        for i in range(n):
            page = doc[i]
            bitmap = page.render(scale=scale)
            pil = bitmap.to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            out.append(buf.getvalue())
        return out
    finally:
        doc.close()


def _render_pdf_fitz(
    path: Path,
    fitz: Any,
    *,
    max_pages: int,
    dpi: int,
) -> list[bytes]:
    doc = fitz.open(str(path))
    try:
        n = min(int(doc.page_count), max(1, int(max_pages)))
        zoom = max(1.0, float(dpi) / 72.0)
        mat = fitz.Matrix(zoom, zoom)
        out: list[bytes] = []
        for i in range(n):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out.append(pix.tobytes("png"))
        return out
    finally:
        doc.close()


def ocr_file(
    path: Path | str,
    *,
    max_pages: int = 40,
    dpi: int = 160,
) -> dict[str, Any]:
    """OCR an image or scanned PDF into plain text."""
    p = Path(path)
    suffix = p.suffix.lower()
    warnings: list[str] = []
    if suffix in _IMAGE_SUFFIXES:
        data = p.read_bytes()
        return ocr_image_bytes(data, filename=p.name)
    if suffix in _PDF_SUFFIXES:
        images = render_pdf_page_images(p, max_pages=max_pages, dpi=dpi)
        if not images:
            return {
                "text": "",
                "page_count": 0,
                "engine": _ocr_engine_name or "ocr",
                "warnings": ["pdf_no_pages"],
            }
        parts: list[str] = []
        engine_name = _ocr_engine_name or "ocr"
        for i, img in enumerate(images):
            page_out = ocr_image_bytes(img, filename=f"page-{i + 1}.png")
            engine_name = str(page_out.get("engine") or engine_name)
            warnings.extend(page_out.get("warnings") or [])
            chunk = (page_out.get("text") or "").strip()
            if chunk:
                parts.append(chunk)
        if len(images) >= max_pages:
            warnings.append(f"truncated_to_{max_pages}_pages")
        return {
            "text": "\n\n".join(parts),
            "page_count": len(images),
            "engine": engine_name,
            "warnings": warnings,
        }
    raise ValueError(f"unsupported_ocr_type:{suffix}")
