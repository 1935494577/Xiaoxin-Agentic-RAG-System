from __future__ import annotations

import json
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

# 必须在任何可能导入 huggingface_hub 的模块之前加载，以便 HF_ENDPOINT 在 hub 缓存 ENDPOINT 前生效
from config import settings

from agent.graph import run_agent
from agent.stream_chat import stream_rag_chat
from agent.conversation_context import resolve_chat_history
from api.chat_memory import chat_memory_settings
from api.prompt_config_store import public_prompt_config, save_prompt_config
from api.routing_mode import apply_hybrid_expert_memory, resolve_hybrid_expert_mode
from api.stream_retrieval import build_stream_retrieval_state, resolve_stream_fast_mode
from api.auth_middleware import APIAuthMiddleware, SecurityHeadersMiddleware
from api.chat_session_store import (
    append_messages,
    create_session,
    delete_session,
    get_session,
    init_chat_session_db,
    list_messages,
    list_sessions,
    update_session_title,
)
from api.connection_cache import get_cached_status, invalidate_status, set_cached_status
from api.llm_resolve import resolve_llm_runtime
from api.llm_test import test_llm_connection
from api.model_profile_store import (
    delete_profile,
    effective_api_base,
    get_default_profile_id,
    get_profile_raw,
    load_store,
    set_default_profile,
    to_public_dict,
    upsert_profile,
)
from api.schemas import (
    ChatMessagePublic,
    ChatMessagesAppend,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionPublic,
    ChatSessionUpdate,
    FeedbackRequest,
    IngestDedupStatsResponse,
    IngestResponse,
    IngestTextRequest,
    ModelProfileCreate,
    ModelProfileListResponse,
    ModelProfilePublic,
    ModelProfileTestRequest,
    ModelProfileUpdate,
    ModelConnectionStatus,
    PreviewRequest,
    PreviewResponse,
    ProcessingToolsPublic,
    ProcessingToolsUpdate,
    PromptConfigPublic,
    PromptConfigUpdate,
    PublicConfigResponse,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
    SourceRef,
    VectorStoreCreate,
    VectorStoreListResponse,
    VectorStorePublic,
    VectorStoreBackendOption,
    UiConfigPublic,
    UiConfigUpdate,
)
from api.vector_store_registry import (
    activate_store,
    create_store,
    delete_store,
    ensure_default_registry,
    list_stores_public,
    reload_all_indexes,
)
from api.ui_config_store import (
    public_ui_config,
    resolve_logo_file,
    save_logo_file,
    save_ui_config,
)
from chunker.parent_child import persist_chunks_jsonl, split_parent_child
from chunker.utils import normalize_ingest_tags
from document_loader.cleaner import clean_file, clean_raw_text
from document_loader.processing.pipeline import process_upload_file
from document_loader.processing.modes import UNCLEANED, normalize_ingest_mode
from document_loader.processing.registry import load_config as load_processing_config
from document_loader.processing.registry import public_config as public_processing_config
from document_loader.processing.registry import save_config as save_processing_config
from api.nav_config import build_nav_config
from evaluation.langsmith_trace import configure_tracing, get_trace_status
from indexing.dedup_text import content_hash
from indexing.embeddings import embed_texts
from indexing.es_indexer import delete_parents_by_source, index_parent_documents
from indexing.ingest_dedup import (
    check_document_duplicate,
    filter_parent_child_duplicates,
    finalize_document_registry,
    prepare_source_reingest,
)
from indexing.milvus_indexer import delete_by_source as milvus_delete_by_source
from indexing.milvus_indexer import init_vector_db, insert_child_vectors


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.hf_endpoint.strip():
        os.environ["HF_ENDPOINT"] = settings.hf_endpoint.strip().rstrip("/")
    configure_tracing()
    init_vector_db()
    init_chat_session_db()
    ensure_default_registry()
    reload_all_indexes()

    def _warmup() -> None:
        import logging

        try:
            from indexing.model_preload import ensure_models_on_disk, warmup_models_in_memory

            ensure_models_on_disk()
            warmup_models_in_memory()
        except Exception:
            logging.getLogger(__name__).exception("Model warmup failed")

    import threading

    if settings.warmup_models_on_startup:
        threading.Thread(target=_warmup, daemon=True).start()
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


@app.get("/config/nav")
def get_nav_config():
    """Unified nav links for Chat SPA and Streamlit admin."""
    return build_nav_config()


@app.get("/debug/trace-status")
def trace_status():
    """Return LangSmith trace configuration (no secrets)."""
    return get_trace_status()


@app.get("/config/public", response_model=PublicConfigResponse)
def public_config():
    """供前端展示当前服务端向量 / 重排 / 默认对话模型（不含密钥）。"""
    return PublicConfigResponse(
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model,
        default_chat_model=settings.openai_chat_model,
        use_presidio_default=settings.use_presidio,
    )


@app.get("/config/ui", response_model=UiConfigPublic)
def get_ui_config():
    return UiConfigPublic.model_validate(public_ui_config())


@app.put("/config/ui", response_model=UiConfigPublic)
def update_ui_config(body: UiConfigUpdate):
    patch = body.model_dump(exclude_unset=True)
    clear_logo = bool(patch.pop("clear_logo_image", False))
    if clear_logo:
        p = resolve_logo_file()
        if p:
            p.unlink(missing_ok=True)
        patch["logo_image_path"] = ""
    cfg = save_ui_config(patch)
    if clear_logo:
        _ = cfg
    return UiConfigPublic.model_validate(public_ui_config())


@app.get("/config/processing-tools", response_model=ProcessingToolsPublic)
def get_processing_tools_config():
    return ProcessingToolsPublic.model_validate(public_processing_config())


@app.put("/config/processing-tools", response_model=ProcessingToolsPublic)
def update_processing_tools_config(body: ProcessingToolsUpdate):
    patch = body.model_dump(exclude_unset=True)
    save_processing_config(patch)
    return ProcessingToolsPublic.model_validate(public_processing_config())


@app.get("/config/prompts", response_model=PromptConfigPublic)
def get_prompt_config(
    mode: str = Query(default="kb", pattern="^(kb|general)$"),
    fast: bool = Query(default=False),
):
    return PromptConfigPublic.model_validate(public_prompt_config(mode=mode, fast=fast))


@app.put("/config/prompts", response_model=PromptConfigPublic)
def update_prompt_config(
    body: PromptConfigUpdate,
    mode: str = Query(default="kb", pattern="^(kb|general)$"),
    fast: bool = Query(default=False),
):
    raw_slots = None
    if body.slots is not None:
        raw_slots = [s.model_dump(exclude_unset=True) for s in body.slots]
    save_prompt_config(slots=raw_slots, reset_defaults=bool(body.reset_defaults))
    return PromptConfigPublic.model_validate(public_prompt_config(mode=mode, fast=fast))


@app.get("/config/vector-stores", response_model=VectorStoreListResponse)
def get_vector_stores():
    """列出向量库配置，含当前活动库与维度兼容状态。"""
    data = list_stores_public()
    return VectorStoreListResponse(
        stores=[VectorStorePublic.model_validate(s) for s in data.get("stores") or []],
        active_store_id=data.get("active_store_id"),
        active=VectorStorePublic.model_validate(data["active"]) if data.get("active") else None,
        available_backends=[
            VectorStoreBackendOption.model_validate(b) for b in data.get("available_backends") or []
        ],
    )


@app.post("/config/vector-stores", response_model=VectorStorePublic)
def post_vector_store(req: VectorStoreCreate):
    try:
        row = create_store(name=req.name, backend=req.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return VectorStorePublic.model_validate(row)


@app.put("/config/vector-stores/{store_id}/activate", response_model=VectorStorePublic)
def put_vector_store_activate(store_id: str):
    try:
        row = activate_store(store_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return VectorStorePublic.model_validate(row)


@app.delete("/config/vector-stores/{store_id}")
def delete_vector_store(store_id: str):
    try:
        delete_store(store_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@app.get("/config/ui/logo")
def get_ui_logo():
    p = resolve_logo_file()
    if not p:
        raise HTTPException(status_code=404, detail="Logo image not configured")
    data = p.read_bytes()
    media = "image/png"
    if p.suffix.lower() in {".jpg", ".jpeg"}:
        media = "image/jpeg"
    elif p.suffix.lower() == ".webp":
        media = "image/webp"
    elif p.suffix.lower() == ".svg":
        media = "image/svg+xml"
    elif p.suffix.lower() == ".gif":
        media = "image/gif"
    return Response(content=data, media_type=media)


@app.post("/config/ui/logo", response_model=UiConfigPublic)
async def upload_ui_logo(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty logo file")
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo file too large (max 2MB)")
    save_logo_file(file.filename or "logo.png", content)
    return UiConfigPublic.model_validate(public_ui_config())


@app.get("/config/model-profiles", response_model=ModelProfileListResponse)
def list_model_profiles():
    data = load_store()
    raw_list = data.get("profiles") or []
    public = [ModelProfilePublic.model_validate(to_public_dict(p)) for p in raw_list]
    return ModelProfileListResponse(
        profiles=public,
        default_profile_id=get_default_profile_id(),
    )


@app.get("/config/model-profiles/connection-status", response_model=ModelConnectionStatus)
def model_connection_status(
    profile_id: str | None = Query(default=None, max_length=64),
    force_env_llm: bool = Query(default=False),
    quick: bool = Query(default=False, description="仅检查密钥是否已配置，不调用大模型"),
    force_check: bool = Query(default=False, description="忽略缓存并重新探测"),
):
    req = ChatRequest(
        message="ping",
        user_id="status_probe",
        model_profile_id=profile_id,
        force_env_llm=force_env_llm,
    )
    runtime = resolve_llm_runtime(req)
    api_key = str(runtime.get("llm_api_key") or "").strip()
    api_base = str(runtime.get("llm_api_base") or "").strip()
    model = str(runtime.get("chat_model") or "").strip()

    if quick:
        if not api_key:
            return ModelConnectionStatus(connected=False, message="未配置 API Key")
        if not api_base:
            return ModelConnectionStatus(connected=False, message="未配置 API Base")
        if not model:
            return ModelConnectionStatus(connected=False, message="未配置模型名称")
        return ModelConnectionStatus(connected=True, message="已配置（未探测）")

    if not force_check:
        cached = get_cached_status(profile_id, force_env_llm)
        if cached is not None:
            ok, msg = cached
            return ModelConnectionStatus(connected=ok, message=msg)

    ok, msg = test_llm_connection(
        api_base=api_base,
        api_key=api_key,
        model=model,
        extra_headers=runtime.get("llm_extra_headers") if isinstance(runtime.get("llm_extra_headers"), dict) else None,
        timeout_sec=8.0,
    )
    set_cached_status(profile_id, force_env_llm, ok, msg)
    return ModelConnectionStatus(connected=ok, message=msg)


@app.post("/config/model-profiles/test", response_model=ModelConnectionStatus)
def test_model_profile_draft(body: ModelProfileTestRequest):
    row = {
        "api_base": body.api_base,
        "api_path": body.api_path,
        "combined_base": "",
        "default_model": body.default_model,
    }
    base = effective_api_base(row)
    ok, msg = test_llm_connection(
        api_base=base,
        api_key=body.api_key,
        model=body.default_model,
        extra_headers=body.extra_headers,
        timeout_sec=8.0,
    )
    return ModelConnectionStatus(connected=ok, message=msg)


@app.get("/config/model-profiles/{profile_id}", response_model=ModelProfilePublic)
def get_model_profile(profile_id: str):
    row = get_profile_raw(profile_id)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ModelProfilePublic.model_validate(to_public_dict(row))


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


@app.post("/config/model-profiles/{profile_id}/test", response_model=ModelConnectionStatus)
def test_saved_model_profile(profile_id: str):
    prof = get_profile_raw(profile_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found")
    ok, msg = test_llm_connection(
        api_base=effective_api_base(prof),
        api_key=str(prof.get("api_key") or ""),
        model=str(prof.get("default_model") or ""),
        extra_headers=prof.get("extra_headers") if isinstance(prof.get("extra_headers"), dict) else None,
        timeout_sec=8.0,
    )
    invalidate_status(profile_id)
    set_cached_status(profile_id, False, ok, msg)
    return ModelConnectionStatus(connected=ok, message=msg)


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


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve(req: RetrieveRequest):
    """检索调试：混合检索 + Rerank，不调用大模型生成答案（无需 API Key）。"""
    from retrieval.hybrid_searcher import hybrid_search
    from security.permissions import filter_by_sources

    rewritten, parents = hybrid_search(
        req.query,
        req.user_department,
        top_k=req.top_k,
        retrieval_dedup=req.retrieval_dedup,
    )
    parents = filter_by_sources(parents, req.allowed_sources)
    hits = [
        RetrieveHit(
            parent_id=str(p.get("parent_id") or ""),
            source=str(p.get("source") or ""),
            department=str(p.get("department") or ""),
            permission_label=str(p.get("permission_label") or ""),
            hybrid_score=float(p["hybrid_score"]) if p.get("hybrid_score") is not None else None,
            rerank_score=float(p["rerank_score"]) if p.get("rerank_score") is not None else None,
            text=str(p.get("text") or ""),
        )
        for p in parents
    ]
    return RetrieveResponse(rewritten_query=rewritten, hits=hits)


def _resolve_request_history(req: ChatRequest, mem: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    mem = mem or chat_memory_settings()
    req_hist = [h.model_dump() for h in req.history] if req.history else None
    return resolve_chat_history(
        request_history=req_hist,
        user_id=req.user_id,
        session_id=req.session_id,
        max_turns=int(mem.get("max_history_turns", 6)),
        max_chars=int(mem.get("max_history_chars", 6000)),
        long_term_enabled=bool(mem.get("long_term_memory_enabled", True)),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """步骤7：对话入口。"""
    runtime = resolve_llm_runtime(req)
    if not (runtime.get("llm_api_key") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="未配置 API Key：请在「模型配置」中保存密钥，或在 .env 中设置 OPENAI_API_KEY。",
        )
    mem = chat_memory_settings()
    out = run_agent(
        question=req.message,
        user_id=req.user_id,
        user_department=req.user_department,
        allowed_sources=req.allowed_sources,
        llm_runtime=runtime,
        history=_resolve_request_history(req, mem),
        memory_config=mem,
    )
    return ChatResponse(
        answer=out.get("answer") or "",
        sources=out.get("sources") or [],
        source_refs=[SourceRef(**r) for r in (out.get("source_refs") or [])],
        rewritten_query=out.get("rewritten_query"),
        answer_mode=out.get("answer_mode"),
        verified=out.get("verified"),
    )


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """SSE 流式对话：检索完成后逐 token 返回答案，末尾返回引用。"""
    runtime = resolve_llm_runtime(req)
    if not (runtime.get("llm_api_key") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="未配置 API Key：请在「模型配置」中保存密钥，或在 .env 中设置 OPENAI_API_KEY。",
        )

    fast = resolve_stream_fast_mode(req.stream_fast_mode)
    hybrid = resolve_hybrid_expert_mode(req.hybrid_expert_mode)
    mem = apply_hybrid_expert_memory(chat_memory_settings(), hybrid)
    history = _resolve_request_history(req, mem)
    state: dict[str, Any] = {
        "question": req.message,
        "user_id": req.user_id,
        "user_department": req.user_department,
        "allowed_sources": req.allowed_sources,
        "history": history,
        "memory_config": mem,
        "quiet_routing": True,
        "hybrid_expert_mode": hybrid,
        "llm_temperature_answer": req.temperature if req.temperature is not None else 0.2,
        "llm_max_tokens_rewrite": req.max_tokens_rewrite if req.max_tokens_rewrite is not None else 128,
        "llm_max_tokens_answer": req.max_tokens_answer,
        "llm_temperature_verifier": req.verifier_temperature,
        "llm_max_tokens_verifier": req.max_tokens_verifier,
    }
    state.update(
        build_stream_retrieval_state(
            fast,
            skip_query_rewrite=req.skip_query_rewrite,
        )
    )
    state.update(runtime)

    def _gen():
        yield from stream_rag_chat(state)

    return StreamingResponse(_gen(), media_type="text/event-stream")


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """步骤7：用户反馈落盘（JSONL）。"""
    settings.data_feedback_path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(timezone.utc).isoformat(), **req.model_dump()}
    with settings.data_feedback_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True}


@app.get("/chat/sessions", response_model=list[ChatSessionPublic])
def chat_sessions_list(user_id: str = Query(..., min_length=1, max_length=128)):
    """按用户 ID 列出对话会话（SQLite 持久化）。"""
    return [ChatSessionPublic.model_validate(s) for s in list_sessions(user_id)]


@app.post("/chat/sessions", response_model=ChatSessionPublic)
def chat_sessions_create(req: ChatSessionCreate):
    row = create_session(req.user_id, title=req.title)
    return ChatSessionPublic.model_validate(row)


@app.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessagePublic])
def chat_session_messages(
    session_id: str,
    user_id: str = Query(..., min_length=1, max_length=128),
):
    if not get_session(session_id, user_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return [ChatMessagePublic.model_validate(m) for m in list_messages(session_id, user_id)]


@app.post("/chat/sessions/{session_id}/messages", response_model=list[ChatMessagePublic])
def chat_session_append(session_id: str, req: ChatMessagesAppend):
    if req.user_id.strip() != req.user_id:
        raise HTTPException(status_code=400, detail="invalid user_id")
    try:
        rows = append_messages(
            session_id,
            req.user_id,
            [m.model_dump(exclude_none=True) for m in req.messages],
            auto_title_from=req.auto_title_from,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return [ChatMessagePublic.model_validate(m) for m in rows]


@app.put("/chat/sessions/{session_id}", response_model=ChatSessionPublic)
def chat_session_update(session_id: str, req: ChatSessionUpdate):
    row = update_session_title(session_id, req.user_id, req.title)
    if not row:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ChatSessionPublic.model_validate(row)


@app.delete("/chat/sessions/{session_id}")
def chat_session_delete(
    session_id: str,
    user_id: str = Query(..., min_length=1, max_length=128),
):
    if not delete_session(session_id, user_id):
        raise HTTPException(status_code=404, detail="会话不存在")
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
        tags=req.tags,
    )


@app.post("/ingest/path", response_model=IngestResponse)
def ingest_path(
    relative_path: str = Query(..., description="Path under enterprise_rag/data/raw"),
    department: str | None = Query(default=None, max_length=64),
    permission_label: str | None = Query(default=None, max_length=64),
    tags: str | None = Query(default=None, max_length=512, description="逗号分隔的入库标签"),
):
    """开发入库（步骤4 小批量调试）；步骤7 未列此端点。"""
    src = _safe_raw_file(relative_path)
    if not src.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    text = clean_file(src, use_presidio=settings.use_presidio)
    rel = str(Path(relative_path).as_posix())
    return _ingest_text(
        text,
        source=rel,
        department=department,
        permission_label=permission_label,
        tags=normalize_ingest_tags(tags),
    )


def _safe_upload_filename(filename: str | None) -> str:
    """Basename only; reject path traversal (.., separators)."""
    raw = (filename or "upload.bin").strip()
    name = Path(raw).name
    if not name or name in {".", ".."} or ".." in raw.replace("\\", "/"):
        raise HTTPException(status_code=400, detail="Invalid upload filename")
    return name


@app.post("/ingest/upload", response_model=IngestResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    department: str | None = Query(default=None, max_length=64),
    permission_label: str | None = Query(default=None, max_length=64),
    use_presidio: bool = Query(default=True, description="兼容旧参数；未清洗模式下由工具链控制"),
    ingest_mode: str = Query(
        default="uncleaned",
        pattern="^(pre_cleaned|uncleaned|cleaned|raw)$",
        description="pre_cleaned=已清洗仅入库；uncleaned=未清洗走工具链（cleaned/raw 为兼容别名）",
    ),
    tags: str | None = Query(default=None, max_length=512, description="逗号分隔的入库标签"),
    use_llm_router: bool | None = Query(default=None),
):
    safe_name = _safe_upload_filename(file.filename)
    ext = Path(safe_name).suffix.lower().lstrip(".")
    allowed = set(public_ui_config().get("supported_upload_extensions") or [])
    if allowed and ext and ext not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: .{ext}")

    settings.data_raw_dir.mkdir(parents=True, exist_ok=True)
    dest = (settings.data_raw_dir / safe_name).resolve()
    try:
        dest.relative_to(settings.data_raw_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload path") from None
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    mode = normalize_ingest_mode(ingest_mode)
    cfg = load_processing_config()
    if use_llm_router is not None:
        cfg["use_llm_router"] = use_llm_router

    llm_runtime: dict[str, Any] | None = None
    if mode == UNCLEANED and cfg.get("use_llm_router", True):
        try:
            probe = ChatRequest(message=".", user_id="ingest")
            llm_runtime = resolve_llm_runtime(probe)
        except Exception:
            llm_runtime = None

    try:
        proc = process_upload_file(dest, mode=mode, llm_runtime=llm_runtime)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    if not proc.text.strip():
        raise HTTPException(status_code=422, detail="未能从文件中提取有效文本，请检查文件内容或格式。")

    result = _ingest_text(
        proc.text,
        source=safe_name,
        department=department,
        permission_label=permission_label,
        tags=normalize_ingest_tags(tags),
    )
    result.ingest_mode = mode
    result.tools_used = proc.tools_used
    result.router = proc.router
    result.file_type = proc.file_type
    if result.chunks_indexed == 0:
        result.message = "文件已处理但未生成可索引片段，请检查内容是否过短。"
    return result


def _ingest_text(
    text: str,
    source: str,
    department: str | None = None,
    permission_label: str | None = None,
    tags: list[str] | None = None,
) -> IngestResponse:
    doc_tags = normalize_ingest_tags(tags)
    settings.data_processed_dir.mkdir(parents=True, exist_ok=True)
    processed = settings.data_processed_dir / Path(source).name
    processed.write_text(text, encoding="utf-8")

    l1 = check_document_duplicate(text, source)
    if l1 and l1.early_exit:
        st = l1.stats
        return IngestResponse(
            chunks_indexed=0,
            source=source,
            tags=doc_tags,
            message=st.message,
            dedup=IngestDedupStatsResponse(
                content_hash=st.content_hash,
                doc_duplicate=True,
                canonical_source=st.canonical_source,
                alias_sources=st.alias_sources,
            ),
        )

    prepare_source_reingest(source)
    milvus_delete_by_source(source)
    delete_parents_by_source(source)

    parents, children = split_parent_child(
        text, source, department, permission_label, tags=doc_tags
    )
    digest = content_hash(text)
    plan = filter_parent_child_duplicates(
        parents, children, source, doc_content_hash=digest
    )
    parents = plan.parents
    children = plan.children
    dedup_stats = plan.stats

    persist_chunks_jsonl(parents, children)
    if not children:
        finalize_document_registry(
            source, text, parent_count=len(parents), child_count=0
        )
        return IngestResponse(
            chunks_indexed=0,
            source=source,
            tags=doc_tags,
            message=dedup_stats.message,
            dedup=IngestDedupStatsResponse(
                content_hash=dedup_stats.content_hash or None,
                skipped_parents=dedup_stats.skipped_parents,
                skipped_children=dedup_stats.skipped_children,
                indexed_parents=dedup_stats.indexed_parents,
                indexed_children=0,
            ),
        )

    mat = embed_texts([c.text for c in children])
    vectors = mat.tolist()
    insert_child_vectors(
        ids=[c.chunk_id for c in children],
        vectors=vectors,
        texts=[c.text for c in children],
        parent_ids=[c.parent_id for c in children],
        departments=[c.department for c in children],
        sources=[c.source for c in children],
        tags=doc_tags,
    )
    parent_docs = [
        {
            "parent_id": p.parent_id,
            "content": p.text,
            "department": p.department,
            "source": p.source,
            "permission_label": p.permission_label,
            "tags": p.tags,
        }
        for p in parents
    ]
    index_parent_documents(parent_docs)
    doc_rec = finalize_document_registry(
        source, text, parent_count=len(parents), child_count=len(children)
    )
    alias_sources = list(doc_rec.alias_sources) if doc_rec else dedup_stats.alias_sources
    return IngestResponse(
        chunks_indexed=len(children),
        source=source,
        tags=doc_tags,
        message=dedup_stats.message,
        dedup=IngestDedupStatsResponse(
            content_hash=dedup_stats.content_hash or None,
            skipped_parents=dedup_stats.skipped_parents,
            skipped_children=dedup_stats.skipped_children,
            indexed_parents=dedup_stats.indexed_parents,
            indexed_children=dedup_stats.indexed_children,
            alias_sources=alias_sources,
        ),
    )
