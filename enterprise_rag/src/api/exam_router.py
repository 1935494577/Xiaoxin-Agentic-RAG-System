"""Exam bank HTTP API — isolated from Chat hot path."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from exam_bank import assemble, store
from exam_bank.subject_catalog import (
    BUILTIN_QTYPES,
    QTYPE_LABELS,
    difficulty_bands_public,
    normalize_qtype,
    qtype_label,
    subject_catalog_public,
)
from exam_bank.types import (
    DEFAULT_TENANT,
    DIFFICULTY_MAX,
    DIFFICULTY_MIN,
    EXAM_SCENE_PRESETS,
)

router = APIRouter(prefix="/api/exam", tags=["exam-bank"])


class CollectionCreate(BaseModel):
    name: str
    subject: str = ""
    grade: str = ""
    region: str = ""
    description: str = ""
    tenant_id: str = DEFAULT_TENANT
    visibility: str = "private"
    owner_user_id: str = ""


class QuestionCreate(BaseModel):
    collection_id: str
    qtype: str = "choice"
    difficulty: int = 3
    stem: str
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    analysis: str = ""
    knowledge_tags: list[str] = Field(default_factory=list)
    region: str = ""
    year: str = ""
    chapter: str = ""
    difficulty_coef: float | None = None
    cognitive_level: str = ""
    discrimination: float | None = None
    textbook_version: str = ""
    subject: str = ""
    grade: str = ""
    quality_status: str = "published"
    tenant_id: str = DEFAULT_TENANT
    source_paper_id: str = ""
    question_no: str = ""


class QuestionUpdate(BaseModel):
    qtype: str | None = None
    difficulty: int | None = None
    stem: str | None = None
    options: list[str] | None = None
    answer: str | None = None
    analysis: str | None = None
    knowledge_tags: list[str] | None = None
    region: str | None = None
    year: str | None = None
    chapter: str | None = None
    difficulty_coef: float | None = None
    cognitive_level: str | None = None
    discrimination: float | None = None
    textbook_version: str | None = None
    subject: str | None = None
    grade: str | None = None
    quality_status: str | None = None
    source_paper_id: str | None = None
    question_no: str | None = None


class AssembleSpec(BaseModel):
    by_qtype: dict[str, int] = Field(default_factory=dict)
    by_difficulty_band: dict[str, int] = Field(default_factory=dict)
    by_qtype_band: dict[str, dict[str, int]] = Field(default_factory=dict)
    difficulty_min: int | None = None
    difficulty_max: int | None = None
    # 目标难度系数 0–1（越高越易）；未填分档时映射为 difficulty_min/max
    difficulty_target_coef: float | None = None
    knowledge_tags_any: list[str] = Field(default_factory=list)
    chapters_any: list[str] = Field(default_factory=list)
    regions_any: list[str] = Field(default_factory=list)
    years_any: list[str] = Field(default_factory=list)
    soft_fallback: bool = False
    seed: int = 0


class AssembleRequest(BaseModel):
    collection_id: str
    title: str = "未命名试卷"
    include_answers: bool = True
    spec: AssembleSpec = Field(default_factory=AssembleSpec)
    tenant_id: str = DEFAULT_TENANT


class SwapQuestionRequest(BaseModel):
    collection_id: str
    question_id: str
    exclude_ids: list[str] = Field(default_factory=list)
    limit: int = 5
    soft_fallback: bool = True


class AssembleNlRequest(BaseModel):
    collection_id: str
    text: str
    title: str = ""
    include_answers: bool = True
    tenant_id: str = DEFAULT_TENANT


class DetectSectionsRequest(BaseModel):
    text: str
    subject: str = ""
    grade: str = ""
    use_llm: bool = True


@router.get("/llm-status")
def exam_llm_status() -> dict[str, Any]:
    """P0: whether exam ingest LLM is configured (does not call the model)."""
    from exam_bank.llm_client import build_openai_client

    client, rt = build_openai_client(timeout_sec=10.0)
    # 拆题用 Chat 主模型，与对话一致
    model = str(rt.get("chat_model") or rt.get("model") or "").strip()
    configured = client is not None and bool(model)
    return {
        "ok": True,
        "configured": configured,
        "model": model,
        "routing_model": str(rt.get("routing_model") or ""),
        "source": str(rt.get("source") or ""),
        "api_base": str(rt.get("llm_api_base") or ""),
        "message": (
            "大模型已配置，智能拆题可用"
            if configured
            else "未配置 API Key / 模型，智能拆题不可用。请在 .env 或 Admin「模型」页配置（与 Chat 同源）。"
        ),
    }


@router.get("/meta")
def exam_meta(
    stage: str = Query(default="junior"),
    grade: str = Query(default=""),
) -> dict[str, Any]:
    from exam_bank.subject_catalog import resolve_stage, stages_public, common_regions_public

    st = resolve_stage(grade, stage)
    labels = {**QTYPE_LABELS}
    from exam_bank.llm_client import resolve_exam_llm_runtime

    llm_rt = resolve_exam_llm_runtime()
    return {
        "available": True,
        "db_path": str(store._db_path()),
        "qtypes": list(BUILTIN_QTYPES),
        "qtype_labels": labels,
        "difficulty_min": DIFFICULTY_MIN,
        "difficulty_max": DIFFICULTY_MAX,
        "difficulty_bands": difficulty_bands_public(),
        "stages": stages_public(),
        "stage": st,
        "subjects": subject_catalog_public(stage=st),
        "common_regions": common_regions_public(),
        "scene_presets": list(EXAM_SCENE_PRESETS),
        "export_formats": ["markdown", "docx", "pdf"],
        "llm": {
            "model": llm_rt.get("model") or "",
            "chat_model": llm_rt.get("chat_model") or "",
            "api_base": llm_rt.get("llm_api_base") or "",
            "source": llm_rt.get("source") or "env",
            "key_configured": bool(str(llm_rt.get("llm_api_key") or "").strip()),
        },
    }


@router.post("/analyze-paper")
def exam_analyze_paper(body: DetectSectionsRequest) -> dict[str, Any]:
    """LLM-first paper routing agent (subject / stage / sections)."""
    from exam_bank.paper_router import analyze_paper

    return analyze_paper(
        body.text,
        subject=body.subject,
        grade=body.grade,
        use_llm=body.use_llm,
    )


@router.post("/detect-sections")
def exam_detect_sections(body: DetectSectionsRequest) -> dict[str, Any]:
    """Alias of analyze-paper for backward compatibility."""
    from exam_bank.paper_router import analyze_paper

    return analyze_paper(
        body.text,
        subject=body.subject,
        grade=body.grade,
        use_llm=body.use_llm,
    )


@router.post("/collections")
def create_collection(body: CollectionCreate) -> dict[str, Any]:
    try:
        return store.create_collection(
            name=body.name,
            subject=body.subject,
            grade=body.grade,
            region=body.region,
            description=body.description,
            tenant_id=body.tenant_id,
            visibility=body.visibility,
            owner_user_id=body.owner_user_id,
        )
    except ValueError as e:
        err = str(e)
        if err == "region_required":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "region_required",
                    "message": "请选择地区：各地区各科单独建库",
                },
            ) from e
        if err == "collection_scope_conflict":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "collection_scope_conflict",
                    "message": "该地区·学科·年级题库已存在，请直接选用",
                },
            ) from e
        if err == "collection_name_conflict":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "collection_name_conflict",
                    "message": "同学科同年级下已存在同名题库，请选用已有或更换名称",
                },
            ) from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/collections")
def list_collections(
    tenant_id: str = Query(default=DEFAULT_TENANT),
    subject: str | None = None,
    grade: str | None = None,
    region: str | None = None,
    reader_user_id: str | None = Query(default=None),
) -> dict[str, Any]:
    rows = store.list_collections(tenant_id=tenant_id, reader_user_id=reader_user_id)
    if subject:
        s = subject.strip()
        rows = [r for r in rows if (r.get("subject") or "") == s]
    if grade:
        g = grade.strip()
        rows = [r for r in rows if (r.get("grade") or "") == g]
    if region:
        rg = region.strip()
        rows = [r for r in rows if (r.get("region") or "") == rg]
    return {"items": rows, "total": len(rows)}


@router.post("/admin/purge")
def exam_admin_purge() -> dict[str, Any]:
    """清空题库全部数据（开发/重置用）。"""
    return store.purge_exam_bank()


@router.get("/collections/{collection_id}")
def get_collection(collection_id: str) -> dict[str, Any]:
    row = store.get_collection(collection_id)
    if not row:
        raise HTTPException(status_code=404, detail="collection_not_found")
    return row


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: str) -> dict[str, Any]:
    if not store.delete_collection(collection_id):
        raise HTTPException(status_code=404, detail="collection_not_found")
    return {"ok": True, "id": collection_id}


@router.post("/questions")
def create_question(body: QuestionCreate) -> dict[str, Any]:
    try:
        return store.create_question(
            collection_id=body.collection_id,
            qtype=normalize_qtype(body.qtype),
            difficulty=body.difficulty,
            stem=body.stem,
            options=body.options,
            answer=body.answer,
            analysis=body.analysis,
            knowledge_tags=body.knowledge_tags,
            region=body.region,
            year=body.year,
            chapter=body.chapter,
            difficulty_coef=body.difficulty_coef,
            cognitive_level=body.cognitive_level,
            discrimination=body.discrimination,
            textbook_version=body.textbook_version,
            subject=body.subject,
            grade=body.grade,
            quality_status=body.quality_status,
            tenant_id=body.tenant_id,
            source_paper_id=body.source_paper_id,
            question_no=body.question_no,
        )
    except ValueError as e:
        if str(e) == "collection_not_found":
            raise HTTPException(status_code=404, detail="collection_not_found") from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/questions/{question_id}")
def update_question(question_id: str, body: QuestionUpdate) -> dict[str, Any]:
    payload = body.model_dump(exclude_unset=True)
    if "qtype" in payload and payload["qtype"] is not None:
        payload["qtype"] = normalize_qtype(payload["qtype"])
    try:
        return store.update_question(question_id, **payload)
    except ValueError as e:
        if str(e) == "question_not_found":
            raise HTTPException(status_code=404, detail="question_not_found") from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/questions/{question_id}")
def delete_question(question_id: str) -> dict[str, Any]:
    if not store.delete_question(question_id):
        raise HTTPException(status_code=404, detail="question_not_found")
    return {"ok": True, "id": question_id}


@router.get("/questions")
def list_questions(
    collection_id: str = Query(...),
    qtype: str | None = None,
    difficulty: int | None = None,
    tag: str | None = None,
    q: str | None = None,
    status: str | None = "published",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items, total = store.list_questions(
        collection_id=collection_id,
        qtype=normalize_qtype(qtype) if qtype else None,
        difficulty=difficulty,
        tag=tag,
        q=q,
        status=None if (status or "").strip().lower() in ("", "all") else status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total}


@router.get("/questions/{question_id}")
def get_question(question_id: str) -> dict[str, Any]:
    row = store.get_question(question_id)
    if not row:
        raise HTTPException(status_code=404, detail="question_not_found")
    return row


@router.post("/papers/assemble")
def assemble_paper(body: AssembleRequest) -> dict[str, Any]:
    col = store.get_collection(body.collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="collection_not_found")
    spec = body.spec.model_dump()
    # 题库即地区作用域：强制按库地区约束出题
    col_region = str(col.get("region") or "").strip()
    if col_region:
        spec["regions_any"] = [col_region]
    result = assemble.assemble_paper(
        collection_id=body.collection_id,
        title=body.title,
        spec=spec,
        include_answers=body.include_answers,
        tenant_id=body.tenant_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/papers/auto-generate")
def auto_generate_paper(body: AssembleRequest) -> dict[str, Any]:
    """11.txt 对齐：智能组卷入口（未显式传 soft_fallback 时默认开启兜底）。"""
    from exam_bank.orchestrator import auto_generate_paper as orch_auto
    from exam_bank.store import difficulty_to_coef

    spec = body.spec.model_dump()
    fields_set = getattr(body.spec, "model_fields_set", set()) or set()
    if "soft_fallback" not in fields_set:
        spec["soft_fallback"] = True
    # Map target ease coef → difficulty band when min/max unset
    coef = spec.get("difficulty_target_coef")
    if coef is not None and spec.get("difficulty_min") is None and spec.get("difficulty_max") is None:
        c = max(0.0, min(1.0, float(coef)))
        # higher coef = easier → lower difficulty int
        if c >= 0.8:
            spec["difficulty_min"], spec["difficulty_max"] = 1, 2
        elif c >= 0.55:
            spec["difficulty_min"], spec["difficulty_max"] = 2, 3
        elif c >= 0.4:
            spec["difficulty_min"], spec["difficulty_max"] = 3, 4
        else:
            spec["difficulty_min"], spec["difficulty_max"] = 4, 5
        _ = difficulty_to_coef  # keep import used for symmetry / future scoring
    result = orch_auto(
        collection_id=body.collection_id,
        title=body.title,
        spec=spec,
        include_answers=body.include_answers,
        tenant_id=body.tenant_id,
    )
    if result.get("error") == "collection_not_found":
        raise HTTPException(status_code=404, detail="collection_not_found")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/questions/swap")
def swap_question(body: SwapQuestionRequest) -> dict[str, Any]:
    from exam_bank.orchestrator import swap_question as orch_swap

    result = orch_swap(
        collection_id=body.collection_id,
        question_id=body.question_id,
        exclude_ids=list(body.exclude_ids or []),
        limit=body.limit,
        soft_fallback=body.soft_fallback,
    )
    if result.get("error") == "question_not_found":
        raise HTTPException(status_code=404, detail="question_not_found")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/papers/assemble-nl")
def assemble_paper_nl(body: AssembleNlRequest) -> dict[str, Any]:
    """P1: one-sentence assemble — NL → spec → paper."""
    if not store.get_collection(body.collection_id):
        raise HTTPException(status_code=404, detail="collection_not_found")
    from exam_bank.nl_assemble import assemble_from_nl

    result = assemble_from_nl(
        collection_id=body.collection_id,
        text=body.text,
        title=body.title,
        include_answers=body.include_answers,
        tenant_id=body.tenant_id,
        soft_fallback=True,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/papers/{paper_id}")
def get_paper(paper_id: str) -> dict[str, Any]:
    row = store.get_paper(paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper_not_found")
    return row


@router.post("/papers/{paper_id}/lesson")
def paper_lesson(paper_id: str) -> dict[str, Any]:
    """P4: generate lesson outline markdown from assembled paper."""
    from exam_bank.lesson import lesson_from_paper

    result = lesson_from_paper(paper_id)
    if not result.get("ok"):
        code = 404 if result.get("error") == "paper_not_found" else 400
        raise HTTPException(status_code=code, detail=result)
    return result


@router.get("/papers/{paper_id}/export")
def export_paper(
    paper_id: str,
    format: str = Query(default="markdown", alias="format"),
    include_answers: bool = Query(default=True),
):
    from urllib.parse import quote

    from fastapi.responses import Response

    from exam_bank.export_formats import EXPORT_FORMATS, export_paper_file

    row = store.get_paper(paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="paper_not_found")
    try:
        data, content_type, filename = export_paper_file(
            row, fmt=format, include_answers=include_answers
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_export_format",
                "message": str(e),
                "allowed": list(EXPORT_FORMATS),
            },
        ) from e
    # RFC 5987 filename* for Chinese titles
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": disposition},
    )


class IngestParseRequest(BaseModel):
    text: str
    subject: str = ""
    grade: str = ""
    region: str = ""
    stage: str = ""
    use_llm: bool = True
    clean: bool = True


class IngestCleanRequest(BaseModel):
    text: str


class IngestItem(BaseModel):
    question_no: str = ""
    qtype: str = "other"
    stem: str
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    analysis: str = ""
    knowledge_tags: list[str] = Field(default_factory=list)
    chapter: str = ""
    year: str = ""
    difficulty: int = 3
    selected: bool = True


class IngestCommitRequest(BaseModel):
    collection_id: str
    title: str = ""
    source_filename: str = ""
    raw_text: str = ""
    region: str = ""
    year: str = ""
    quality_status: str = "published"
    items: list[IngestItem] = Field(default_factory=list)
    tenant_id: str = DEFAULT_TENANT
    media_ingest_id: str = ""


class ApplyAnswersRequest(BaseModel):
    source_paper_id: str
    answer_text: str


def _guess_paper_year(*parts: str) -> str:
    import re

    for p in parts:
        m = re.search(r"(20\d{2})", p or "")
        if m:
            return m.group(1)
    return ""


@router.get("/inventory")
def exam_inventory(
    collection_id: str = Query(...),
    tag: list[str] | None = Query(default=None),
    chapter: list[str] | None = Query(default=None),
    region: list[str] | None = Query(default=None),
    year: list[str] | None = Query(default=None),
) -> dict[str, Any]:
    from exam_bank.subject_catalog import qtype_label

    inv = store.collection_inventory(
        collection_id,
        tags_any=list(tag or []),
        chapters_any=list(chapter or []),
        regions_any=list(region or []),
        years_any=list(year or []),
    )
    labeled = [
        {"id": k, "label": qtype_label(k), "count": v}
        for k, v in sorted((inv.get("by_qtype") or {}).items(), key=lambda x: (-x[1], x[0]))
    ]
    inv["by_qtype_labeled"] = labeled
    return inv


@router.post("/ingest/clean")
def ingest_clean(body: IngestCleanRequest) -> dict[str, Any]:
    """清洗试卷正文：去注意事项、切开粘连选项，保留 [[EQ:n]]。"""
    from exam_bank.paper_clean import clean_exam_paper

    return clean_exam_paper(body.text or "")


@router.post("/ingest/parse")
def ingest_parse(body: IngestParseRequest) -> dict[str, Any]:
    from exam_bank.item_split import parse_paper_items

    result = parse_paper_items(
        body.text,
        subject=body.subject,
        grade=body.grade,
        region=body.region,
        stage=body.stage,
        use_llm=body.use_llm,
        clean=body.clean,
    )
    result.setdefault("raw_text", body.text)
    return result


@router.post("/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    subject: str = Form(default=""),
    grade: str = Form(default=""),
    region: str = Form(default=""),
    stage: str = Form(default=""),
    use_llm: bool = Form(default=True),
    clean: bool = Form(default=True),
) -> dict[str, Any]:
    import tempfile
    from pathlib import Path

    from document_loader.parser import load_document_text
    from exam_bank.docx_extract import default_exam_media_root, extract_docx_exam
    from exam_bank.item_split import parse_paper_items

    suffix = Path(file.filename or "paper.txt").suffix.lower() or ".txt"
    if suffix not in {".pdf", ".docx", ".doc", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="unsupported_file_type")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty_file")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)
    media: list[dict[str, Any]] = []
    extract_warnings: list[str] = []
    ingest_id = ""
    try:
        if suffix == ".docx":
            extracted = extract_docx_exam(
                tmp_path,
                media_dir=default_exam_media_root(),
            )
            text = str(extracted.get("text") or "")
            media = list(extracted.get("media") or [])
            extract_warnings = list(extracted.get("warnings") or [])
            ingest_id = str(extracted.get("ingest_id") or "")
        else:
            text = load_document_text(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"parse_failed: {e}") from e
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
    result = parse_paper_items(
        text,
        subject=subject,
        grade=grade,
        region=region,
        stage=stage,
        use_llm=use_llm,
        clean=clean,
    )
    result["source_filename"] = file.filename or ""
    result["raw_text"] = text
    result["media"] = [
        {
            "eq_id": m.get("eq_id"),
            "filename": m.get("saved_as") or m.get("filename"),
            "ingest_id": ingest_id,
            "url": (
                f"/api/exam/ingest/media/{ingest_id}/{m.get('saved_as') or m.get('filename')}"
                if ingest_id and (m.get("saved_as") or m.get("filename"))
                else ""
            ),
        }
        for m in media
        if m.get("eq_id")
    ]
    result["extract_warnings"] = extract_warnings
    result["ingest_id"] = ingest_id
    result["eq_count"] = len(media)
    return result


@router.get("/ingest/ocr/status")
def ingest_ocr_status() -> dict[str, Any]:
    """Whether optional PaddleOCR deps are installed."""
    from exam_bank.ocr_ingest import ocr_status

    return ocr_status()


@router.post("/ingest/ocr")
async def ingest_ocr(
    file: UploadFile = File(...),
    subject: str = Form(default=""),
    grade: str = Form(default=""),
    region: str = Form(default=""),
    stage: str = Form(default=""),
    use_llm: bool = Form(default=True),
    clean: bool = Form(default=True),
    max_pages: int = Form(default=40),
) -> dict[str, Any]:
    """OCR scanned PDF / image → clean → split (no CamScanner required)."""
    import tempfile
    from pathlib import Path as _Path

    from exam_bank.item_split import parse_paper_items
    from exam_bank.ocr_ingest import ocr_file, ocr_status

    status = ocr_status()
    if not status.get("available"):
        missing = ", ".join(status.get("missing") or ["paddleocr"])
        hint = status.get("hint") or "pip install -r requirements-exam-optional.txt"
        raise HTTPException(
            status_code=503,
            detail=f"ocr_unavailable: missing {missing}. {hint}",
        )

    suffix = _Path(file.filename or "scan.png").suffix.lower() or ".png"
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="unsupported_ocr_file_type")
    if suffix == ".pdf" and not status.get("pdf_render_ready"):
        raise HTTPException(
            status_code=503,
            detail="ocr_pdf_needs_renderer: pip install pypdfium2  (see requirements-exam-optional.txt)",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty_file")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = _Path(tmp.name)
    ocr_meta: dict[str, Any]
    try:
        ocr_meta = ocr_file(tmp_path, max_pages=max(1, min(int(max_pages), 80)))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ocr_failed: {e}") from e
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    text = str(ocr_meta.get("text") or "")
    if not text.strip():
        raise HTTPException(status_code=422, detail="ocr_empty_text")

    result = parse_paper_items(
        text,
        subject=subject,
        grade=grade,
        region=region,
        stage=stage,
        use_llm=use_llm,
        clean=clean,
    )
    result["source_filename"] = file.filename or ""
    result["raw_text"] = text
    result["ocr_applied"] = True
    result["ocr_engine"] = ocr_meta.get("engine")
    result["ocr_page_count"] = ocr_meta.get("page_count")
    result["ocr_warnings"] = list(ocr_meta.get("warnings") or [])
    return result


@router.get("/ingest/media/{ingest_id}/eq/{eq_id}")
def ingest_eq_media(ingest_id: str, eq_id: str):
    """Resolve [[EQ:n]] to the extracted image under exam_media/{ingest_id}/."""
    from exam_bank.docx_extract import default_exam_media_root, resolve_eq_media_file

    path = resolve_eq_media_file(default_exam_media_root(), ingest_id, eq_id)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="eq_media_not_found")
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".wmf": "image/x-wmf",
        ".emf": "image/x-emf",
    }.get(path.suffix.lower())
    return FileResponse(path, media_type=media_type)


@router.get("/ingest/media/{ingest_id}/{filename}")
def ingest_media(ingest_id: str, filename: str):
    """Serve extracted equation / figure files for ingest preview."""
    from exam_bank.docx_extract import default_exam_media_root

    safe_id = "".join(c for c in ingest_id if c.isalnum() or c in "-_")
    safe_name = Path(filename).name
    if not safe_id or not safe_name or ".." in filename:
        raise HTTPException(status_code=400, detail="invalid_media_path")
    path = default_exam_media_root() / safe_id / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="media_not_found")
    return FileResponse(path)


@router.post("/ingest/commit")
def ingest_commit(body: IngestCommitRequest) -> dict[str, Any]:
    col = store.get_collection(body.collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="collection_not_found")
    selected = [it for it in body.items if it.selected and (it.stem or "").strip()]
    if not selected:
        raise HTTPException(status_code=400, detail="no_items_selected")
    status = (body.quality_status or "published").strip().lower()
    paper_region = str(col.get("region") or "").strip()
    if not paper_region:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "collection_region_missing",
                "message": "题库未设置地区，请新建「地区·学科·年级」题库后再入库",
            },
        )
    paper_year = (body.year or "").strip() or _guess_paper_year(
        body.title, body.source_filename
    )
    created: list[dict[str, Any]] = []
    media_id = (body.media_ingest_id or "").strip()
    for it in selected:
        q = store.create_question(
            collection_id=body.collection_id,
            qtype=normalize_qtype(it.qtype),
            stem=it.stem,
            options=it.options,
            answer=it.answer,
            analysis=it.analysis,
            knowledge_tags=list(it.knowledge_tags or []),
            chapter=(it.chapter or "").strip(),
            region=paper_region,
            year=(it.year or "").strip() or paper_year,
            subject=str(col.get("subject") or "").strip(),
            grade=str(col.get("grade") or "").strip(),
            difficulty=int(it.difficulty or 3),
            quality_status=status,
            tenant_id=body.tenant_id,
            question_no=it.question_no,
            media_ingest_id=media_id,
        )
        created.append(q)
    sp = store.create_source_paper(
        collection_id=body.collection_id,
        title=body.title or body.source_filename or "导入试卷",
        source_filename=body.source_filename,
        raw_text=body.raw_text,
        question_ids=[q["id"] for q in created],
        tenant_id=body.tenant_id,
        media_ingest_id=media_id,
    )
    for q in created:
        store.update_question(q["id"], source_paper_id=sp["id"])
        q["source_paper_id"] = sp["id"]
    return {"source_paper": sp, "questions": created, "total": len(created)}


@router.post("/ingest/apply-answers")
def ingest_apply_answers(body: ApplyAnswersRequest) -> dict[str, Any]:
    from exam_bank.item_split import parse_answer_key

    sp = store.get_source_paper(body.source_paper_id)
    if not sp:
        raise HTTPException(status_code=404, detail="source_paper_not_found")
    mapping = parse_answer_key(body.answer_text)
    updated = []
    unmatched: list[str] = []
    for qid in sp.get("question_ids") or []:
        q = store.get_question(qid)
        if not q:
            continue
        no = str(q.get("question_no") or "").strip()
        if no and no in mapping:
            row = store.update_question(qid, answer=mapping[no])
            updated.append(row)
        else:
            unmatched.append(no or qid)
    store.update_source_paper(body.source_paper_id, answer_text=body.answer_text)
    return {
        "ok": True,
        "updated": len(updated),
        "unmatched": unmatched,
        "source_paper": store.get_source_paper(body.source_paper_id),
    }


@router.get("/source-papers")
def list_source_papers(collection_id: str = Query(...)) -> dict[str, Any]:
    rows = store.list_source_papers(collection_id=collection_id)
    return {"items": rows, "total": len(rows)}


@router.get("/source-papers/{source_paper_id}")
def get_source_paper(source_paper_id: str) -> dict[str, Any]:
    row = store.get_source_paper(source_paper_id)
    if not row:
        raise HTTPException(status_code=404, detail="source_paper_not_found")
    return row


class PaperFromQuestionsRequest(BaseModel):
    collection_id: str
    title: str = "自选试卷"
    question_ids: list[str] = Field(default_factory=list)
    include_answers: bool = True
    tenant_id: str = DEFAULT_TENANT


@router.post("/papers/from-questions")
def paper_from_questions(body: PaperFromQuestionsRequest) -> dict[str, Any]:
    """试题篮定稿：按已选题序生成试卷快照。"""
    if not store.get_collection(body.collection_id):
        raise HTTPException(status_code=404, detail="collection_not_found")
    ids = [str(x).strip() for x in (body.question_ids or []) if str(x).strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="no_questions")
    ordered: list[dict[str, Any]] = []
    for qid in ids:
        q = store.get_question(qid)
        if not q or q.get("collection_id") != body.collection_id:
            raise HTTPException(status_code=400, detail=f"invalid_question:{qid}")
        ordered.append(q)
    md = assemble.render_markdown(
        title=body.title or "自选试卷",
        ordered=ordered,
        include_answers=body.include_answers,
    )
    paper = store.save_paper(
        collection_id=body.collection_id,
        title=body.title or "自选试卷",
        spec={"from_basket": True, "question_ids": ids},
        question_ids=ids,
        markdown=md,
        tenant_id=body.tenant_id,
    )
    return {
        "ok": True,
        "paper_id": paper["id"],
        "title": paper["title"],
        "question_ids": ids,
        "questions": ordered,
        "markdown": md,
        "counts": {},
    }
