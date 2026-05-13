from __future__ import annotations

import json
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

# 必须在任何可能导入 huggingface_hub 的模块之前加载，以便 HF_ENDPOINT 在 hub 缓存 ENDPOINT 前生效
from config import settings

from agent.graph import run_agent
from api.auth_middleware import APIAuthMiddleware, SecurityHeadersMiddleware
from api.llm_resolve import resolve_llm_runtime
from api.model_profile_store import (
    delete_profile,
    get_default_profile_id,
    load_store,
    set_default_profile,
    to_public_dict,
    upsert_profile,
)
from api.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    IngestResponse,
    IngestTextRequest,
    ModelProfileCreate,
    ModelProfileListResponse,
    ModelProfilePublic,
    ModelProfileUpdate,
    PreviewRequest,
    PreviewResponse,
    PublicConfigResponse,
)
from chunker.parent_child import persist_chunks_jsonl, split_parent_child
from document_loader.cleaner import clean_file, clean_raw_text
from evaluation.langsmith_trace import configure_tracing
from indexing.embeddings import embed_texts
from indexing.es_indexer import delete_parents_by_source, index_parent_documents
from indexing.milvus_indexer import delete_by_source as milvus_delete_by_source
from indexing.milvus_indexer import init_vector_db, insert_child_vectors


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.hf_endpoint.strip():
        os.environ["HF_ENDPOINT"] = settings.hf_endpoint.strip().rstrip("/")
    configure_tracing()
    init_vector_db()
    yield


app = FastAPI(
    title="Enterprise RAG API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.disable_openapi_docs else "/docs",
    redoc_url=None if settings.disable_openapi_docs else "/redoc",
    openapi_url=None if settings.disable_openapi_docs else "/openapi.json",
)

_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
_allow_origins = _origins if _origins else ["*"]
_allow_creds = bool(_origins) and "*" not in _allow_origins

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(APIAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_creds,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

_hosts = [h.strip() for h in settings.trusted_hosts.split(",") if h.strip()]
if _hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_hosts)


@app.get("/", include_in_schema=False)
def root():
    """根路径：开发态跳转文档；生产关闭文档时返回 JSON。"""
    if settings.disable_openapi_docs:
        return {"service": "Enterprise RAG API", "health": "/health"}
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


def _safe_raw_file(relative_path: str) -> Path:
    root = settings.data_raw_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path: escapes data/raw")
    return candidate


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config/public", response_model=PublicConfigResponse)
def public_config():
    """供前端展示当前服务端向量 / 重排 / 默认对话模型（不含密钥）。"""
    return PublicConfigResponse(
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model,
        default_chat_model=settings.openai_chat_model,
        use_presidio_default=settings.use_presidio,
    )


@app.get("/config/model-profiles", response_model=ModelProfileListResponse)
def list_model_profiles():
    data = load_store()
    raw_list = data.get("profiles") or []
    public = [ModelProfilePublic.model_validate(to_public_dict(p)) for p in raw_list]
    return ModelProfileListResponse(
        profiles=public,
        default_profile_id=get_default_profile_id(),
    )


@app.post("/config/model-profiles", response_model=ModelProfilePublic)
def create_model_profile(body: ModelProfileCreate):
    row = upsert_profile(
        profile_id=None,
        name=body.name,
        vendor=body.vendor,
        api_base=body.api_base,
        api_path=body.api_path,
        default_model=body.default_model,
        api_key=body.api_key,
        extra_headers=body.extra_headers,
    )
    return ModelProfilePublic.model_validate(to_public_dict(row))


@app.put("/config/model-profiles/{profile_id}", response_model=ModelProfilePublic)
def update_model_profile(profile_id: str, body: ModelProfileUpdate):
    try:
        existing = None
        for p in load_store().get("profiles") or []:
            if str(p.get("id")) == profile_id:
                existing = p
                break
        if not existing:
            raise HTTPException(status_code=404, detail="Profile not found")
        row = upsert_profile(
            profile_id=profile_id,
            name=body.name if body.name is not None else str(existing.get("name") or ""),
            vendor=body.vendor if body.vendor is not None else str(existing.get("vendor") or "custom"),
            api_base=body.api_base if body.api_base is not None else str(existing.get("api_base") or ""),
            api_path=body.api_path if body.api_path is not None else existing.get("api_path"),
            default_model=body.default_model if body.default_model is not None else str(existing.get("default_model") or ""),
            api_key=body.api_key,
            extra_headers=body.extra_headers if body.extra_headers is not None else existing.get("extra_headers"),
        )
        return ModelProfilePublic.model_validate(to_public_dict(row))
    except KeyError:
        raise HTTPException(status_code=404, detail="Profile not found") from None


@app.delete("/config/model-profiles/{profile_id}")
def remove_model_profile(profile_id: str):
    if not delete_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"ok": True}


@app.post("/config/model-profiles/{profile_id}/default")
def set_default_model_profile(profile_id: str):
    try:
        set_default_profile(profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Profile not found") from None
    return {"ok": True, "default_profile_id": profile_id}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """步骤7：对话入口。"""
    runtime = resolve_llm_runtime(req)
    if not (runtime.get("llm_api_key") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="未配置 API Key：请在「模型配置」中保存密钥，或在 .env 中设置 OPENAI_API_KEY。",
        )
    out = run_agent(
        question=req.message,
        user_id=req.user_id,
        user_department=req.user_department,
        allowed_sources=req.allowed_sources,
        llm_runtime=runtime,
    )
    return ChatResponse(
        answer=out.get("answer") or "",
        sources=out.get("sources") or [],
        rewritten_query=out.get("rewritten_query"),
    )


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """步骤7：用户反馈落盘（JSONL）。"""
    settings.data_feedback_path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(timezone.utc).isoformat(), **req.model_dump()}
    with settings.data_feedback_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True}


@app.post("/ingest/preview", response_model=PreviewResponse)
def ingest_preview(req: PreviewRequest):
    """仅清洗预览，不入库。"""
    cleaned = clean_raw_text(req.text, use_presidio=req.use_presidio)
    return PreviewResponse(cleaned=cleaned)


@app.post("/ingest/text", response_model=IngestResponse)
def ingest_text(req: IngestTextRequest):
    """粘贴文本：清洗后切块、写入向量库与 BM25 索引。"""
    text = clean_raw_text(req.text, use_presidio=req.use_presidio)
    return _ingest_text(
        text,
        source=req.source,
        department=req.department,
        permission_label=req.permission_label,
    )


@app.post("/ingest/path", response_model=IngestResponse)
def ingest_path(
    relative_path: str = Query(..., description="Path under enterprise_rag/data/raw"),
    department: str | None = Query(default=None, max_length=64),
    permission_label: str | None = Query(default=None, max_length=64),
):
    """开发入库（步骤4 小批量调试）；步骤7 未列此端点。"""
    src = _safe_raw_file(relative_path)
    if not src.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    text = clean_file(src, use_presidio=settings.use_presidio)
    rel = str(Path(relative_path).as_posix())
    return _ingest_text(text, source=rel, department=department, permission_label=permission_label)


@app.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    department: str | None = Query(default=None, max_length=64),
    permission_label: str | None = Query(default=None, max_length=64),
):
    settings.data_raw_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.data_raw_dir / (file.filename or "upload.bin")
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    text = clean_file(dest, use_presidio=settings.use_presidio)
    return _ingest_text(
        text,
        source=file.filename or dest.name,
        department=department,
        permission_label=permission_label,
    )


def _ingest_text(
    text: str,
    source: str,
    department: str | None = None,
    permission_label: str | None = None,
) -> IngestResponse:
    settings.data_processed_dir.mkdir(parents=True, exist_ok=True)
    processed = settings.data_processed_dir / Path(source).name
    processed.write_text(text, encoding="utf-8")

    milvus_delete_by_source(source)
    delete_parents_by_source(source)

    parents, children = split_parent_child(text, source, department, permission_label)
    persist_chunks_jsonl(parents, children)
    if not children:
        return IngestResponse(chunks_indexed=0, source=source)

    mat = embed_texts([c.text for c in children])
    vectors = mat.tolist()
    insert_child_vectors(
        ids=[c.chunk_id for c in children],
        vectors=vectors,
        texts=[c.text for c in children],
        parent_ids=[c.parent_id for c in children],
        departments=[c.department for c in children],
        sources=[c.source for c in children],
    )
    parent_docs = [
        {
            "parent_id": p.parent_id,
            "content": p.text,
            "department": p.department,
            "source": p.source,
            "permission_label": p.permission_label,
        }
        for p in parents
    ]
    index_parent_documents(parent_docs)
    return IngestResponse(chunks_indexed=len(children), source=source)
