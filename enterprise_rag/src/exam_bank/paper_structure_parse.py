"""Exam paper structure parse: PP-StructureV3 (+ LaTeXOCR) → reading order → LLM JSON.

Pipeline
--------
1. ``.docx`` / ``.doc`` → python-docx / ``docx_extract`` (embedded formulas as blocks)
2. Image / scanned PDF → rasterize → ``PPStructureV3`` with formula recognition
   (``formula_recognition_model_name=LaTeX_OCR_rec``)
3. Reorder layout blocks; formulas kept as LaTeX
4. Optional DeepSeek (OpenAI-compatible) post-process → per-question JSON

Install (heavy; optional)::

    pip install "paddleocr[doc-parser]>=3.0" paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

Logging: module logger ``exam_bank.paper_structure_parse``.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

_log = logging.getLogger(__name__)

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
_PDF_SUFFIXES = {".pdf"}
_DOCX_SUFFIXES = {".docx"}
_DOC_SUFFIXES = {".doc"}

_FORMULA_LABELS = {"formula", "equation", "display_formula", "inline_formula"}

_LLM_SYSTEM = """你是中小学数学/综合试卷结构化助手。输入是 OCR 重组后的阅读顺序文本，其中公式已用 $...$ 或 \\(...\\) 包裹的 LaTeX。

任务：按题号切分试题，提取每道题的题干、选项、答案、解析。

硬性要求：
1. 只输出 JSON，不要 Markdown 围栏。
2. 保留公式的 LaTeX（$...$），不要把公式改成乱码或省略。
3. 丢弃注意事项、装订线、页眉页脚、纯大题标题（无题干时）。
4. qtype 使用：choice|fill|short|calc|experiment|cloze|reading|writing|listening|material|other。
5. options 保留 "A. …" 原文；无选项则 []。
6. 无答案/解析时用空字符串。

输出 schema：
{
  "questions": [
    {
      "question_no": "1",
      "qtype": "choice",
      "stem": "题干（可含 $LaTeX$）",
      "options": ["A. …", "B. …"],
      "answer": "",
      "analysis": ""
    }
  ]
}
"""

_pipeline: Any = None
_pipeline_error: str = ""


def structure_parse_status() -> dict[str, Any]:
    """Probe optional deps without loading heavy models."""
    missing: list[str] = []
    pp_ok = False
    pp_err = ""
    try:
        from paddleocr import PPStructureV3  # type: ignore  # noqa: F401

        pp_ok = True
    except Exception as e:  # noqa: BLE001
        pp_err = str(e)
        missing.append("paddleocr[doc-parser]")

    pdf_ok = False
    try:
        import pypdfium2  # noqa: F401

        pdf_ok = True
    except Exception:
        try:
            import fitz  # noqa: F401

            pdf_ok = True
        except Exception:
            missing.append("pypdfium2")

    docx_ok = False
    try:
        import docx  # noqa: F401

        docx_ok = True
    except Exception:
        missing.append("python-docx")

    hint = ""
    if not pp_ok:
        hint = (
            'pip install "paddleocr[doc-parser]>=3.0.0" paddlepaddle '
            "-i https://www.paddlepaddle.org.cn/packages/stable/cpu/"
        )
    return {
        "available": pp_ok or docx_ok,
        "pp_structurev3": pp_ok,
        "pp_structurev3_error": pp_err,
        "pdf_render": pdf_ok,
        "python_docx": docx_ok,
        "missing": missing,
        "hint": hint,
        # Prefer PP-FormulaNet on CPU; LaTeX_OCR_rec forces mkldnn and crashes on Paddle 3.3.x
        "formula_model": "PP-FormulaNet_plus-M",
    }


def get_ppstructure_pipeline(
    *,
    device: str | None = None,
    force_reload: bool = False,
) -> Any:
    """Lazy singleton ``PPStructureV3`` with LaTeX formula recognition enabled."""
    global _pipeline, _pipeline_error
    if force_reload:
        _pipeline = None
        _pipeline_error = ""
    if _pipeline is not None:
        return _pipeline
    if _pipeline_error:
        raise RuntimeError(_pipeline_error)
    try:
        from paddleocr import PPStructureV3  # type: ignore
    except Exception as e:  # noqa: BLE001
        _pipeline_error = f"PPStructureV3 unavailable: {e}"
        _log.exception("import PPStructureV3 failed")
        raise RuntimeError(_pipeline_error) from e

    # PaddlePaddle 3.3.x + oneDNN/PIR crashes on CPU
    # (ConvertPirAttribute2RuntimeAttribute ArrayAttribute). Force paddle run_mode.
    base: dict[str, Any] = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_formula_recognition": True,
        # Speed: exam papers rarely need table/seal/chart branches
        "use_table_recognition": False,
        "use_seal_recognition": False,
        "use_chart_recognition": False,
    }
    if device:
        base["device"] = device
    # Prefer disable mkldnn; older paddleocr may reject unknown kwargs → peel off.
    # LaTeX_OCR_rec forces mkldnn on Intel CPU and hits Paddle 3.3.x PIR bugs.
    # PP-FormulaNet_plus-M still emits LaTeX and works with enable_mkldnn=False.
    formula_models = ("PP-FormulaNet_plus-M", "LaTeX_OCR_rec")
    attempts: list[dict[str, Any]] = []
    for fm in formula_models:
        attempts.append(
            {**base, "formula_recognition_model_name": fm, "enable_mkldnn": False}
        )
    attempts.append({**base, "enable_mkldnn": False})
    for fm in formula_models:
        attempts.append({**base, "formula_recognition_model_name": fm})
    attempts.append(dict(base))
    last_err: Exception | None = None
    for kw in attempts:
        try:
            _pipeline = PPStructureV3(**kw)
            _log.info(
                "PPStructureV3 ready (formula_model=%s, mkldnn=%s)",
                kw.get("formula_recognition_model_name"),
                kw.get("enable_mkldnn"),
            )
            return _pipeline
        except TypeError as e:
            last_err = e
            _log.warning("PPStructureV3 TypeError with keys=%s: %s", sorted(kw), e)
            continue
        except Exception as e:  # noqa: BLE001
            _pipeline_error = f"PPStructureV3 init failed: {e}"
            _log.exception("PPStructureV3 init failed")
            raise RuntimeError(_pipeline_error) from e
    _pipeline_error = f"PPStructureV3 init failed: {last_err}"
    raise RuntimeError(_pipeline_error) from last_err


def _bbox_list(raw: Any) -> list[float]:
    try:
        if raw is None:
            return []
        if hasattr(raw, "tolist"):
            flat = raw.tolist()
        else:
            flat = list(raw)
        # nested [[x1,y1],[x2,y2],...] → flatten first 4
        if flat and isinstance(flat[0], (list, tuple)):
            xs = [float(p[0]) for p in flat]
            ys = [float(p[1]) for p in flat]
            return [min(xs), min(ys), max(xs), max(ys)]
        return [float(x) for x in flat[:4]]
    except Exception:  # noqa: BLE001
        return []


def _label_to_type(label: str) -> str:
    lab = (label or "").strip().lower()
    if lab in _FORMULA_LABELS or "formula" in lab:
        return "formula"
    if lab in {"table"}:
        return "table"
    if lab in {"image", "figure", "chart"}:
        return "image"
    return "text"


def parsing_res_list_to_blocks(page: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert one PP-StructureV3 page dict into normalized blocks."""
    page_index = page.get("page_index")
    if page_index is None:
        page_index = 0
    blocks: list[dict[str, Any]] = []
    items = page.get("parsing_res_list") or []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        label = str(it.get("block_label") or it.get("label") or "text")
        content = str(it.get("block_content") or it.get("content") or "").strip()
        if not content and label.lower() not in _FORMULA_LABELS:
            continue
        order = it.get("block_order")
        if order is None:
            order = it.get("block_id", i)
        try:
            order_i = int(order)
        except Exception:  # noqa: BLE001
            order_i = i
        btype = _label_to_type(label)
        # formula_res_list may carry LaTeX separately
        if btype == "formula":
            latex = str(it.get("rec_formula") or content).strip()
            content = latex
        blocks.append(
            {
                "type": btype,
                "content": content,
                "page": int(page_index),
                "order": order_i,
                "bbox": _bbox_list(it.get("block_bbox") or it.get("coordinate")),
                "label": label,
            }
        )

    # Also fold formula_res_list if present and not already covered
    for fr in page.get("formula_res_list") or []:
        if not isinstance(fr, dict):
            continue
        latex = str(fr.get("rec_formula") or "").strip()
        if not latex:
            continue
        blocks.append(
            {
                "type": "formula",
                "content": latex,
                "page": int(page_index),
                "order": 10_000 + len(blocks),
                "bbox": _bbox_list(fr.get("rec_polys") or fr.get("coordinate")),
                "label": "formula",
            }
        )
    return normalize_structure_blocks(blocks)


def normalize_structure_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort by page → order → bbox y/x."""
    def key(b: dict[str, Any]) -> tuple:
        page = int(b.get("page") or 0)
        order = b.get("order")
        try:
            order_i = int(order) if order is not None else 10**9
        except Exception:  # noqa: BLE001
            order_i = 10**9
        bbox = b.get("bbox") or []
        y = float(bbox[1]) if len(bbox) > 1 else 0.0
        x = float(bbox[0]) if len(bbox) > 0 else 0.0
        return (page, order_i, y, x)

    out = [dict(b) for b in blocks if (b.get("content") or "").strip() or b.get("type") == "image"]
    out.sort(key=key)
    # reassign contiguous order for stability
    for i, b in enumerate(out):
        b["order"] = i
    return out


def blocks_to_reading_text(blocks: list[dict[str, Any]], *, latex_delim: str = "$") -> str:
    """Join blocks in reading order; formulas as LaTeX with delimiters."""
    parts: list[str] = []
    for b in normalize_structure_blocks(blocks):
        content = (b.get("content") or "").strip()
        if not content:
            continue
        if b.get("type") == "formula":
            latex = content.strip().strip("$")
            parts.append(f"{latex_delim}{latex}{latex_delim}")
        elif b.get("type") == "table":
            parts.append(content)
        else:
            parts.append(content)
    # light glue: avoid double newlines between inline formula and text
    text = " ".join(parts)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Prefer line breaks before question numbers
    text = re.sub(r"(?<!\n)(\d{1,3}[\.、．]\s*)", r"\n\1", text)
    return text.strip()


def _result_to_page_dict(res: Any) -> dict[str, Any]:
    if isinstance(res, dict):
        return res
    data = getattr(res, "json", None)
    if callable(data):
        try:
            data = data()
        except Exception:  # noqa: BLE001
            data = None
    if isinstance(data, dict):
        # some versions nest under "res"
        if "parsing_res_list" in data:
            return data
        inner = data.get("res")
        if isinstance(inner, dict):
            return inner
        return data
    # fallback attributes
    return {
        "page_index": getattr(res, "page_index", 0),
        "parsing_res_list": getattr(res, "parsing_res_list", []) or [],
        "formula_res_list": getattr(res, "formula_res_list", []) or [],
    }


def run_ppstructure_on_path(
    path: Path | str,
    *,
    device: str | None = None,
    pipeline: Any | None = None,
) -> list[dict[str, Any]]:
    """Run PP-StructureV3 on an image or PDF path; return normalized blocks."""
    p = Path(path)
    eng = pipeline or get_ppstructure_pipeline(device=device)
    _log.info("PP-StructureV3 predict: %s", p)
    try:
        outputs = eng.predict(str(p))
    except Exception as e:  # noqa: BLE001
        _log.exception("PP-StructureV3 predict failed for %s", p)
        raise RuntimeError(f"ppstructure_predict_failed:{e}") from e
    blocks: list[dict[str, Any]] = []
    for res in outputs or []:
        page = _result_to_page_dict(res)
        blocks.extend(parsing_res_list_to_blocks(page))
    return normalize_structure_blocks(blocks)


def extract_docx_blocks(path: Path | str) -> tuple[list[dict[str, Any]], list[str]]:
    """Extract reading blocks from DOCX via python-docx + MathType/OLE placeholders."""
    warnings: list[str] = []
    p = Path(path)
    blocks: list[dict[str, Any]] = []
    order = 0

    # Prefer project extractor (keeps [[EQ:n]] + media)
    try:
        from exam_bank.docx_extract import extract_docx_exam

        extracted = extract_docx_exam(p, media_dir=None)
        text = str(extracted.get("text") or "")
        if extracted.get("eq_count"):
            warnings.append(f"docx_eq_placeholders:{extracted.get('eq_count')}")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # split inline [[EQ:n]] into formula-ish placeholders
            parts = re.split(r"(\[\[EQ:\d+\]\])", line)
            for part in parts:
                if not part:
                    continue
                m = re.fullmatch(r"\[\[EQ:(\d+)\]\]", part)
                if m:
                    # Keep [[EQ:n]] so export can resolve media; do not fake LaTeX.
                    blocks.append(
                        {
                            "type": "text",
                            "content": part,
                            "page": 0,
                            "order": order,
                            "bbox": [],
                            "label": "embedded_eq",
                        }
                    )
                else:
                    blocks.append(
                        {
                            "type": "text",
                            "content": part,
                            "page": 0,
                            "order": order,
                            "bbox": [],
                            "label": "text",
                        }
                    )
                order += 1
        if blocks:
            return normalize_structure_blocks(blocks), warnings
    except Exception as e:  # noqa: BLE001
        warnings.append(f"docx_extract_fallback:{e}")
        _log.warning("docx_extract failed, fallback python-docx: %s", e)

    try:
        from docx import Document  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"python-docx required for Word ingest: {e}") from e

    doc = Document(str(p))
    for para in doc.paragraphs:
        t = (para.text or "").strip()
        if not t:
            continue
        blocks.append(
            {
                "type": "text",
                "content": t,
                "page": 0,
                "order": order,
                "bbox": [],
                "label": "text",
            }
        )
        order += 1
    if not blocks:
        warnings.append("docx_empty")
    return normalize_structure_blocks(blocks), warnings


def render_pdf_to_images(path: Path, *, max_pages: int = 40, dpi: int = 180) -> list[Path]:
    """Rasterize PDF pages to temp PNGs; caller should clean up parent dir."""
    import tempfile

    from exam_bank.ocr_ingest import render_pdf_page_images

    images = render_pdf_page_images(path, max_pages=max_pages, dpi=dpi)
    if not images:
        return []
    tmp = Path(tempfile.mkdtemp(prefix="exam_ppstruct_"))
    out: list[Path] = []
    for i, data in enumerate(images):
        fp = tmp / f"page_{i + 1:03d}.png"
        fp.write_bytes(data)
        out.append(fp)
    return out


def _extract_json_obj(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json|JSON)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw).strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _normalize_questions(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for it in raw:
        if not isinstance(it, dict):
            continue
        stem = str(it.get("stem") or "").strip()
        if not stem:
            continue
        opts = it.get("options") or []
        if not isinstance(opts, list):
            opts = []
        out.append(
            {
                "question_no": str(it.get("question_no") or "").strip(),
                "qtype": str(it.get("qtype") or "other").strip() or "other",
                "stem": stem,
                "options": [str(x) for x in opts if str(x).strip()],
                "answer": str(it.get("answer") or "").strip(),
                "analysis": str(it.get("analysis") or "").strip(),
            }
        )
    return out


def llm_structure_questions(
    reading_text: str,
    *,
    subject: str = "",
    grade: str = "",
    timeout_sec: float = 180.0,
) -> dict[str, Any]:
    """DeepSeek / OpenAI-compatible post-process → questions JSON."""
    blob = (reading_text or "").strip()
    if not blob:
        return {"ok": False, "error": "empty_text", "questions": [], "message": "OCR 文本为空"}

    try:
        from exam_bank.llm_client import build_openai_client
    except Exception as e:  # noqa: BLE001
        _log.exception("llm_client import failed")
        return {"ok": False, "error": "llm_client_missing", "questions": [], "message": str(e)}

    client, rt = build_openai_client(timeout_sec=timeout_sec)
    if client is None:
        return {
            "ok": False,
            "error": "llm_not_configured",
            "questions": [],
            "message": "未配置 DeepSeek/OpenAI API Key（模型页或 .env）",
            "runtime": {k: rt.get(k) for k in ("source", "model", "chat_model") if k in rt},
        }
    model = str(rt.get("chat_model") or rt.get("model") or "").strip()
    if not model:
        return {"ok": False, "error": "llm_model_missing", "questions": [], "message": "未设置模型名"}

    user_payload = {
        "meta": {"subject": subject, "grade": grade},
        "paper_text": blob[:20000],
    }
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": 0.0,
        "max_tokens": 8192,
    }
    try:
        try:
            kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("response_format", None)
            resp = client.chat.completions.create(**kwargs)
        content = (resp.choices[0].message.content or "").strip()
        parsed = _extract_json_obj(content)
        if not parsed:
            _log.warning("LLM returned non-JSON: %s", content[:200])
            return {
                "ok": False,
                "error": "llm_json_parse_failed",
                "questions": [],
                "message": "大模型未返回合法 JSON",
                "raw_preview": content[:400],
            }
        questions = _normalize_questions(parsed.get("questions") or parsed.get("items"))
        return {
            "ok": True,
            "questions": questions,
            "model": model,
            "source": rt.get("source"),
        }
    except Exception as e:  # noqa: BLE001
        _log.exception("LLM structure call failed")
        return {
            "ok": False,
            "error": "llm_call_failed",
            "questions": [],
            "message": str(e),
        }


def parse_exam_paper(
    path: Path | str,
    *,
    use_llm: bool = True,
    subject: str = "",
    grade: str = "",
    max_pages: int = 40,
    dpi: int = 144,
    device: str | None = None,
    llm_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Parse an exam paper file into structured JSON.

    Returns::
        {
          "ok": bool,
          "source": str,
          "source_type": "docx"|"pdf"|"image"|"doc",
          "engine": str,
          "blocks": [...],
          "reading_order_text": str,
          "questions": [...],
          "warnings": [...],
          "error": str|None,
          "message": str,
        }
    """
    p = Path(path)
    warnings: list[str] = []
    if not p.is_file():
        return {
            "ok": False,
            "source": str(p),
            "source_type": "",
            "engine": "",
            "blocks": [],
            "reading_order_text": "",
            "questions": [],
            "warnings": [],
            "error": "file_not_found",
            "message": f"文件不存在: {p}",
        }

    suffix = p.suffix.lower()
    blocks: list[dict[str, Any]] = []
    engine = ""
    source_type = ""

    try:
        if suffix in _DOCX_SUFFIXES:
            source_type = "docx"
            engine = "python-docx+docx_extract"
            blocks, w = extract_docx_blocks(p)
            warnings.extend(w)
        elif suffix in _DOC_SUFFIXES:
            source_type = "doc"
            engine = "legacy_doc"
            # best-effort: convert hint — try text loader
            try:
                from document_loader.parser import load_document_text

                text = str(load_document_text(p) or "")
                for i, line in enumerate(text.splitlines()):
                    if line.strip():
                        blocks.append(
                            {
                                "type": "text",
                                "content": line.strip(),
                                "page": 0,
                                "order": i,
                                "bbox": [],
                                "label": "text",
                            }
                        )
                warnings.append("legacy_doc_plain_text_only")
            except Exception as e:  # noqa: BLE001
                return {
                    "ok": False,
                    "source": str(p),
                    "source_type": source_type,
                    "engine": engine,
                    "blocks": [],
                    "reading_order_text": "",
                    "questions": [],
                    "warnings": warnings,
                    "error": "doc_load_failed",
                    "message": str(e),
                }
        elif suffix in _IMAGE_SUFFIXES:
            source_type = "image"
            engine = "pp-structurev3"
            blocks = run_ppstructure_on_path(p, device=device)
        elif suffix in _PDF_SUFFIXES:
            source_type = "pdf"
            engine = "pp-structurev3"
            # Direct PDF predict is slower/fragile on CPU; rasterize pages first.
            page_paths = render_pdf_to_images(p, max_pages=max_pages, dpi=dpi)
            if not page_paths:
                raise RuntimeError("pdf_no_pages")
            try:
                for pi, page_path in enumerate(page_paths):
                    page_blocks = run_ppstructure_on_path(page_path, device=device)
                    for b in page_blocks:
                        b["page"] = pi
                    blocks.extend(page_blocks)
            finally:
                try:
                    parent = page_paths[0].parent
                    for fp in page_paths:
                        fp.unlink(missing_ok=True)
                    parent.rmdir()
                except Exception:  # noqa: BLE001
                    pass
            blocks = normalize_structure_blocks(blocks)
        else:
            return {
                "ok": False,
                "source": str(p),
                "source_type": suffix.lstrip(".") or "unknown",
                "engine": "",
                "blocks": [],
                "reading_order_text": "",
                "questions": [],
                "warnings": [],
                "error": "unsupported_type",
                "message": f"不支持的文件类型: {suffix}",
            }
    except Exception as e:  # noqa: BLE001
        _log.exception("parse_exam_paper failed: %s", p)
        return {
            "ok": False,
            "source": str(p),
            "source_type": source_type or suffix.lstrip("."),
            "engine": engine,
            "blocks": [],
            "reading_order_text": "",
            "questions": [],
            "warnings": warnings,
            "error": "parse_failed",
            "message": str(e),
        }

    blocks = normalize_structure_blocks(blocks)
    reading = blocks_to_reading_text(blocks)
    questions: list[dict[str, Any]] = []
    llm_meta: dict[str, Any] = {}

    if use_llm:
        fn = llm_fn or llm_structure_questions
        try:
            llm_out = fn(reading, subject=subject, grade=grade)
        except TypeError:
            llm_out = fn(reading)
        llm_meta = {k: v for k, v in llm_out.items() if k != "questions"}
        if llm_out.get("ok"):
            questions = list(llm_out.get("questions") or [])
        else:
            warnings.append(f"llm:{llm_out.get('error') or 'failed'}")
            if llm_out.get("message"):
                warnings.append(str(llm_out["message"]))

    ok = bool(blocks) or bool(questions)
    return {
        "ok": ok,
        "source": str(p.resolve()),
        "source_type": source_type,
        "engine": engine,
        "blocks": blocks,
        "reading_order_text": reading,
        "questions": questions,
        "warnings": warnings,
        "error": None if ok else "empty_result",
        "message": "ok" if ok else "未识别到有效内容",
        "llm": llm_meta,
        "block_count": len(blocks),
        "question_count": len(questions),
    }


def parse_exam_paper_to_json_file(
    path: Path | str,
    out_path: Path | str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Parse and write UTF-8 JSON file; returns the same dict."""
    result = parse_exam_paper(path, **kwargs)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _log.info("wrote structure JSON → %s (ok=%s questions=%s)", out, result.get("ok"), result.get("question_count"))
    return result


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Parse exam paper → structured JSON")
    parser.add_argument(
        "path",
        nargs="?",
        default="",
        help="PDF / image / DOCX path（--status 时可省略）",
    )
    parser.add_argument("-o", "--output", default="", help="Output JSON path")
    parser.add_argument("--no-llm", action="store_true", help="Skip DeepSeek post-process")
    parser.add_argument("--subject", default="")
    parser.add_argument("--grade", default="")
    parser.add_argument("--device", default="", help="e.g. cpu or gpu:0")
    parser.add_argument("--status", action="store_true", help="Print dependency status and exit")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(structure_parse_status(), ensure_ascii=False, indent=2))
        sys.exit(0)
    if not (args.path or "").strip():
        parser.error("请提供试卷路径 path，或使用 --status")
    out = args.output or str(Path(args.path).with_suffix(".structure.json"))
    result = parse_exam_paper_to_json_file(
        args.path,
        out,
        use_llm=not args.no_llm,
        subject=args.subject,
        grade=args.grade,
        device=args.device or None,
    )
    print(json.dumps({"ok": result.get("ok"), "out": out, "questions": result.get("question_count"), "warnings": result.get("warnings")}, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)
