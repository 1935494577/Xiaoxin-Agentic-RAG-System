"""Exam bank HTTP API — isolated from Chat hot path."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
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
    subject: str = ""
    grade: str = ""
    quality_status: str = "published"
    tenant_id: str = DEFAULT_TENANT


class AssembleSpec(BaseModel):
    by_qtype: dict[str, int] = Field(default_factory=dict)
    by_difficulty_band: dict[str, int] = Field(default_factory=dict)
    difficulty_min: int | None = None
    difficulty_max: int | None = None
    knowledge_tags_any: list[str] = Field(default_factory=list)
    seed: int = 0


class AssembleRequest(BaseModel):
    collection_id: str
    title: str = "未命名试卷"
    include_answers: bool = True
    spec: AssembleSpec = Field(default_factory=AssembleSpec)
    tenant_id: str = DEFAULT_TENANT


class DetectSectionsRequest(BaseModel):
    text: str
    subject: str = ""
    grade: str = ""
    use_llm: bool = True


@router.get("/meta")
def exam_meta(
    stage: str = Query(default="junior"),
    grade: str = Query(default=""),
) -> dict[str, Any]:
    from exam_bank.subject_catalog import resolve_stage, stages_public

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
        "scene_presets": list(EXAM_SCENE_PRESETS),
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


@router.get("/collections")
def list_collections(
    tenant_id: str = Query(default=DEFAULT_TENANT),
    subject: str | None = None,
    grade: str | None = None,
    reader_user_id: str | None = Query(default=None),
) -> dict[str, Any]:
    rows = store.list_collections(tenant_id=tenant_id, reader_user_id=reader_user_id)
    if subject:
        s = subject.strip()
        rows = [r for r in rows if (r.get("subject") or "") == s]
    if grade:
        g = grade.strip()
        rows = [r for r in rows if (r.get("grade") or "") == g]
    return {"items": rows, "total": len(rows)}


@router.get("/collections/{collection_id}")
def get_collection(collection_id: str) -> dict[str, Any]:
    row = store.get_collection(collection_id)
    if not row:
        raise HTTPException(status_code=404, detail="collection_not_found")
    return row


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
            subject=body.subject,
            grade=body.grade,
            quality_status=body.quality_status,
            tenant_id=body.tenant_id,
        )
    except ValueError as e:
        if str(e) == "collection_not_found":
            raise HTTPException(status_code=404, detail="collection_not_found") from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/questions")
def list_questions(
    collection_id: str = Query(...),
    qtype: str | None = None,
    difficulty: int | None = None,
    tag: str | None = None,
    status: str | None = "published",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items, total = store.list_questions(
        collection_id=collection_id,
        qtype=normalize_qtype(qtype) if qtype else None,
        difficulty=difficulty,
        tag=tag,
        status=status,
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
    if not store.get_collection(body.collection_id):
        raise HTTPException(status_code=404, detail="collection_not_found")
    result = assemble.assemble_paper(
        collection_id=body.collection_id,
        title=body.title,
        spec=body.spec.model_dump(),
        include_answers=body.include_answers,
        tenant_id=body.tenant_id,
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
