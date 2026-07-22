from __future__ import annotations

import json
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

# 必须在任何可能导入 huggingface_hub 的模块之前加载，以便 HF_ENDPOINT 在 hub 缓存 ENDPOINT 前生效
from config import settings

from agent.graph import run_agent
from agent.stream_chat import stream_rag_chat
from agent.conversation_context import resolve_chat_history
from agent.conversation.prepare import prepare_turn
from api.chat_memory import chat_memory_settings
from account_config.store import init_platform_config_db


def _memory_for_user(request: Request | None, user_id: str | None) -> dict[str, Any]:
    from account_config.request_auth import resolve_config_actor

    auth_uid, _ = resolve_config_actor(request) if request else (None, False)
    actor = auth_uid or ((user_id or "").strip() or None)
    return chat_memory_settings(actor)


from api.department_chat_profile import apply_department_chat_profile
from api.prompt_config_store import public_prompt_config, save_prompt_config
from api.chat_routing import apply_routing_tier
from api.routing_mode import apply_hybrid_expert_memory
from api.stream_retrieval import build_stream_retrieval_state, resolve_stream_fast_mode
from api.admin_roles import AdminRoleMiddleware
from api.auth_middleware import APIAuthMiddleware, SecurityHeadersMiddleware
from api.department_auth import DepartmentFeatureMiddleware
from auth.middleware import SessionAuthMiddleware
from auth.router import router as auth_router
from auth.service import seed_default_users_if_empty
from auth.store import init_auth_db
from api.feedback_router import router as feedback_router
from tenant.context import TenantContextMiddleware, get_tenant_id
from api.chat_session_store import (
    append_messages,
    clear_rolling_summary,
    create_session,
    delete_session,
    get_rolling_summary,
    get_session,
    init_chat_session_db,
    list_messages,
    list_sessions,
    update_session_title,
)
from agent.conversation.rolling_summary import refresh_rolling_summary_for_session
from api.connection_cache import get_cached_status, invalidate_status, set_cached_status
from api.llm_resolve import resolve_llm_runtime
from api.llm_test import test_llm_connection
from api.speech_transcribe import ALLOWED_CONTENT_TYPES, transcribe_audio_bytes
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
    DomainLexiconRebuildResponse,
    EphemeralDocPublic,
    IngestDedupStatsResponse,
    IngestedSourcePublic,
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
    RelationshipImportRequest,
    RelationshipImportResponse,
    ProcessingToolsPublic,
    ProcessingToolsUpdate,
    PromptConfigPublic,
    PromptConfigUpdate,
    PublicConfigResponse,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
    SourcePreviewResponse,
    SourceRef,
    TranscribeResponse,
    VectorStoreCreate,
    VectorStoreListResponse,
    VectorStorePublic,
    VectorStoreBackendOption,
    UiConfigPublic,
    UiConfigUpdate,
    UserProfilePublic,
    UserProfileUpdate,
    LegacyProfileMergeRequest,
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
    load_ui_config,
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
from agent.tools.api.router import router as agent_tools_router
from api.nav_config import build_nav_config
from evaluation.langsmith_trace import configure_tracing, get_trace_status
from feedback_loop.store import init_feedback_db
from indexing.dedup_text import content_hash
from indexing.embeddings import embed_texts
from indexing.es_indexer import delete_parents_by_source, fetch_parents_by_ids, index_parent_documents
from indexing.ingest_dedup import (
    check_document_duplicate,
    filter_parent_child_duplicates,
    finalize_document_registry,
    prepare_source_reingest,
)
from indexing.document_registry import get_document_registry
from api.user_profile_store import (
    apply_auth_to_profile,
    get_profile as get_user_profile,
    init_user_profile_db,
    merge_legacy_user,
    upsert_profile as upsert_user_profile,
)
from indexing.milvus_indexer import delete_by_source as milvus_delete_by_source, init_vector_db, insert_child_vectors


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.hf_endpoint.strip():
        os.environ["HF_ENDPOINT"] = settings.hf_endpoint.strip().rstrip("/")
    configure_tracing()
    init_vector_db()
    init_chat_session_db()
    from api.token_usage_store import init_token_usage_db

    init_token_usage_db()
    init_user_profile_db()
    init_platform_config_db()
    init_auth_db()
    seed_default_users_if_empty()
    init_feedback_db()
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

    from jnao_harness.runtime_bootstrap import harness_runtime_lifespan

    async with harness_runtime_lifespan(app):
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
app.add_middleware(TenantContextMiddleware)
app.add_middleware(AdminRoleMiddleware)
app.add_middleware(DepartmentFeatureMiddleware)
app.add_middleware(APIAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_creds,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)
app.add_middleware(SessionAuthMiddleware)

_hosts = [h.strip() for h in settings.trusted_hosts.split(",") if h.strip()]
if _hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_hosts)

app.include_router(auth_router)
app.include_router(agent_tools_router)
app.include_router(feedback_router)
app.include_router(feedback_router, prefix="/api/v1")

try:
    from api.ops_digest_router import router as ops_digest_router

    app.include_router(ops_digest_router)
except ImportError:
    pass

try:
    from jnao_harness.gateway.routers.channel_connections import router as channel_connections_router

    app.include_router(channel_connections_router)
except ImportError:
    pass

try:
    from jnao_harness.gateway.routers.channels import router as channels_router

    app.include_router(channels_router)
except ImportError:
    pass

try:
    from jnao_harness.gateway.routers.token_usage import router as token_usage_router
    from jnao_harness.gateway.routers.token_usage import summary_router as token_usage_summary_router

    app.include_router(token_usage_router)
    app.include_router(token_usage_summary_router)
except ImportError:
    pass

try:
    from jnao_harness.gateway.routers.skills import router as skills_router

    app.include_router(skills_router)
except ImportError:
    pass


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


@app.get("/health/llm")
def health_llm():
    """Probe default LLM (.env / default model profile) for connectivity."""
    from api.schemas import ChatRequest

    runtime = resolve_llm_runtime(ChatRequest(message="ping", user_id="health"))
    ok, msg = test_llm_connection(
        api_base=str(runtime.get("llm_api_base") or ""),
        api_key=str(runtime.get("llm_api_key") or ""),
        model=str(runtime.get("chat_model") or ""),
        extra_headers=runtime.get("llm_extra_headers") if isinstance(runtime.get("llm_extra_headers"), dict) else None,
        timeout_sec=10.0,
    )
    return {
        "connected": ok,
        "message": msg,
        "model": runtime.get("chat_model"),
        "api_base": runtime.get("llm_api_base"),
    }


@app.get("/config/nav")
def get_nav_config():
    """Nav links for Chat SPA and React admin (see frontend/src/lib/departmentAccess.ts)."""
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
def get_ui_config(request: Request):
    from account_config.store import effective_ui_config
    from account_config.request_auth import resolve_config_actor

    user_id, can_write = resolve_config_actor(request)
    return UiConfigPublic.model_validate(effective_ui_config(user_id))


@app.get("/config/layer-status")
def get_config_layer_status(request: Request):
    """平台配置版本与用户私有覆盖（调试 / 管理）。"""
    from account_config.store import get_platform_version, list_user_config_scopes
    from account_config.request_auth import resolve_config_actor

    from account_config.request_auth import resolve_config_actor

    user_id, can_write = resolve_config_actor(request)
    scopes = ["ui", "processing_tools", "agent_tools", "prompts:kb:std", "prompts:general:std"]
    from auth.middleware import get_auth_user

    auth = get_auth_user(request)
    return {
        "user_id": user_id,
        "username": str(auth.get("username") or "") if auth else "",
        "can_write_platform": can_write,
        "platform_writer": settings.platform_config_writer_username,
        "platform_versions": {s: get_platform_version(s) for s in scopes},
        "user_override_scopes": list_user_config_scopes(user_id) if user_id else [],
    }


@app.get("/config/content-kit")
def get_content_kit(channel: str | None = Query(default=None, max_length=32)):
    """新媒体/小程序集成：引导选项 + 结构化输出模板（企微、视频号、抖音等）。"""
    from agent.clarify import list_clarify_options, normalize_channel
    from agent.output_schemas import list_output_schemas_public

    ch = normalize_channel(channel)
    return {
        "channel": ch,
        "clarify_options": list_clarify_options(channel=ch),
        "output_schemas": list_output_schemas_public(channel=ch),
    }


@app.get("/config/scenario-catalog")
def get_scenario_catalog(
    department: str | None = Query(default=None, max_length=64),
    include_tech: bool | None = Query(default=None),
):
    """业务场景目录：各部门可见自己的功能说明；技术部默认含开发指标与 API。"""
    from api.scenario_catalog import public_scenario_catalog

    return public_scenario_catalog(department, include_tech=include_tech)


@app.post("/admin/eval/kb-health")
def admin_kb_health_probe(
    limit: int = Query(default=30, ge=5, le=80),
    use_llm_judge: bool = Query(default=False),
):
    """零 golden 知识库健康探针：自动问句 → 检索命中率。"""
    from evaluation.kb_health_probe import run_kb_health_probe, write_kb_health_report

    llm_runtime = None
    if use_llm_judge:
        from api.llm_resolve import resolve_llm_runtime
        from api.schemas import ChatRequest

        llm_runtime = resolve_llm_runtime(ChatRequest(message=".", user_id="kb_health"))
    report = run_kb_health_probe(limit=limit, use_llm_judge=use_llm_judge, llm_runtime=llm_runtime)
    if report.get("ok"):
        write_kb_health_report(report)
    return report


@app.put("/config/ui", response_model=UiConfigPublic)
def update_ui_config(body: UiConfigUpdate, request: Request):
    from account_config.store import effective_ui_config, save_platform_scope, save_user_scope_patch
    from account_config.request_auth import resolve_config_actor

    user_id, can_write = resolve_config_actor(request)
    patch = body.model_dump(exclude_unset=True)
    clear_logo = bool(patch.pop("clear_logo_image", False))
    preset_id = patch.pop("scene_preset", None)
    if preset_id and can_write:
        from api.scene_presets import apply_scene_preset

        try:
            apply_scene_preset(str(preset_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif preset_id and user_id:
        save_user_scope_patch(user_id, "ui", {"scene_preset": str(preset_id)})
    if clear_logo and can_write:
        p = resolve_logo_file()
        if p:
            p.unlink(missing_ok=True)
        patch["logo_image_path"] = ""
    if patch:
        if can_write:
            save_ui_config(patch)
            save_platform_scope("ui", updated_by=user_id or "")
        elif user_id:
            save_user_scope_patch(user_id, "ui", patch)
        else:
            raise HTTPException(status_code=401, detail="登录后才能保存个人配置")
    if clear_logo and can_write:
        _ = load_ui_config()
    return UiConfigPublic.model_validate(effective_ui_config(user_id))


@app.post("/config/ui/scene-preset/{preset_id}", response_model=UiConfigPublic)
def apply_ui_scene_preset(preset_id: str):
    from api.scene_presets import apply_scene_preset

    try:
        apply_scene_preset(preset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UiConfigPublic.model_validate(public_ui_config())


@app.get("/config/processing-tools", response_model=ProcessingToolsPublic)
def get_processing_tools_config(request: Request):
    from account_config.store import effective_processing_tools
    from account_config.request_auth import resolve_config_actor

    user_id, can_write = resolve_config_actor(request)
    return ProcessingToolsPublic.model_validate(effective_processing_tools(user_id))


@app.put("/config/processing-tools", response_model=ProcessingToolsPublic)
def update_processing_tools_config(body: ProcessingToolsUpdate, request: Request):
    from account_config.store import effective_processing_tools, save_platform_scope, save_user_scope_patch
    from account_config.request_auth import resolve_config_actor

    user_id, can_write = resolve_config_actor(request)
    patch = body.model_dump(exclude_unset=True)
    if patch:
        if can_write:
            save_processing_config(patch)
            save_platform_scope("processing_tools", updated_by=user_id or "")
        elif user_id:
            save_user_scope_patch(user_id, "processing_tools", patch)
        else:
            raise HTTPException(status_code=401, detail="登录后才能保存个人配置")
    return ProcessingToolsPublic.model_validate(effective_processing_tools(user_id))


@app.get("/config/prompts", response_model=PromptConfigPublic)
def get_prompt_config(
    request: Request,
    mode: str = Query(default="kb", pattern="^(kb|general)$"),
    fast: bool = Query(default=False),
):
    from account_config.store import effective_prompt_bundle
    from account_config.request_auth import resolve_config_actor

    user_id, can_write = resolve_config_actor(request)
    return PromptConfigPublic.model_validate(
        effective_prompt_bundle(user_id, mode=mode, fast=fast)
    )


@app.put("/config/prompts", response_model=PromptConfigPublic)
def update_prompt_config(
    body: PromptConfigUpdate,
    request: Request,
    mode: str = Query(default="kb", pattern="^(kb|general)$"),
    fast: bool = Query(default=False),
):
    from account_config.store import (
        effective_prompt_bundle,
        save_platform_scope,
        save_user_scope_patch,
    )
    from account_config.request_auth import resolve_config_actor

    user_id, can_write = resolve_config_actor(request)
    scope = f"prompts:{mode}:{'fast' if fast else 'std'}"
    raw_slots = None
    if body.slots is not None:
        raw_slots = [s.model_dump(exclude_unset=True) for s in body.slots]

    if can_write:
        if body.agent_reasoning_mode is not None:
            ui = load_ui_config()
            ui["agent_reasoning_mode"] = body.agent_reasoning_mode
            save_ui_config(ui)
        save_prompt_config(
            slots=raw_slots,
            reset_defaults=bool(body.reset_defaults),
            active_persona_id=body.active_persona_id,
        )
        save_platform_scope(scope, updated_by=user_id or "")
    elif user_id:
        user_patch: dict = {}
        if raw_slots is not None:
            user_patch["slots"] = raw_slots
        if body.active_persona_id is not None:
            user_patch["active_persona_id"] = body.active_persona_id
        if body.agent_reasoning_mode is not None:
            user_patch["agent_reasoning_mode"] = body.agent_reasoning_mode
        if body.reset_defaults:
            user_patch["reset_defaults"] = True
        if user_patch:
            save_user_scope_patch(user_id, scope, user_patch)
    else:
        raise HTTPException(status_code=401, detail="登录后才能保存个人配置")

    return PromptConfigPublic.model_validate(
        effective_prompt_bundle(user_id, mode=mode, fast=fast)
    )


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
        routing_model=body.routing_model,
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
            routing_model=body.routing_model if body.routing_model is not None else existing.get("routing_model"),
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


@app.get("/sources/preview/{parent_id}", response_model=SourcePreviewResponse)
def source_preview(
    parent_id: str,
    user_department: str = Query(default="general", max_length=64),
    allowed_sources: str | None = Query(default=None),
):
    """Return parent chunk text for citation preview (ACL + optional source allowlist)."""
    from security.access_control import can_access_row
    from security.permissions import filter_by_sources

    row = fetch_parents_by_ids([parent_id]).get(parent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Parent not found")
    if not can_access_row(row, user_department):
        raise HTTPException(status_code=403, detail="Forbidden")
    allow_list: list[str] | None = None
    if allowed_sources is not None:
        allow_list = [s.strip() for s in allowed_sources.split(",") if s.strip()]
    if not filter_by_sources([row], allow_list):
        raise HTTPException(status_code=403, detail="Forbidden")
    return SourcePreviewResponse(
        parent_id=parent_id,
        source=str(row.get("source") or ""),
        department=str(row.get("department") or ""),
        permission_label=str(row.get("permission_label") or ""),
        text=str(row.get("text") or ""),
    )


@app.get("/sources/list", response_model=list[IngestedSourcePublic])
def sources_list():
    """List ingested document sources for Chat source filter."""
    reg = get_document_registry()
    rows: list[IngestedSourcePublic] = []
    seen: set[str] = set()
    for h, doc in (reg._docs or {}).items():  # noqa: SLF001 — admin/list helper
        src = str(doc.get("canonical_source") or "")
        if not src or src in seen:
            continue
        seen.add(src)
        rows.append(
            IngestedSourcePublic(
                source=src,
                parent_count=int(doc.get("parent_count") or 0),
                child_count=int(doc.get("child_count") or 0),
            )
        )
    return sorted(rows, key=lambda r: r.source)


@app.delete("/sources/{source:path}")
def sources_delete(source: str):
    """Remove an ingested document and its vectors from the knowledge base."""
    from indexing.source_delete import delete_ingested_source

    if not delete_ingested_source(source):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"ok": True}


@app.post("/chat/documents/upload", response_model=EphemeralDocPublic)
async def chat_document_upload(
    file: UploadFile = File(...),
    session_id: str = Query(..., min_length=1, max_length=64),
    user_id: str = Query(..., min_length=1, max_length=128),
    department: str | None = Query(default=None, max_length=64),
):
    """Upload a temporary document for session-scoped Q&A (Classic RAG)."""
    from chat_ephemeral.store import save_ephemeral_document
    from document_loader.cleaner import clean_file

    safe_name = _safe_upload_filename(file.filename)
    raw = await file.read()
    tmp = settings.data_processed_dir / f"ephemeral_{session_id}_{safe_name}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(raw)
    try:
        text = clean_file(tmp, use_presidio=settings.use_presidio)
    finally:
        tmp.unlink(missing_ok=True)
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")
    doc = save_ephemeral_document(
        session_id=session_id,
        user_id=user_id,
        filename=safe_name,
        text=text,
        department=department,
    )
    return EphemeralDocPublic(doc_id=doc.doc_id, filename=doc.filename, session_id=doc.session_id)


@app.post("/chat/transcribe", response_model=TranscribeResponse)
async def chat_transcribe(
    file: UploadFile = File(...),
    language: str = Query(default="zh", max_length=16),
):
    """Upload short audio and transcribe via Whisper (fallback when browser speech API unavailable)."""
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="不支持的音频格式")
    raw = await file.read()
    safe_name = _safe_upload_filename(file.filename) or "speech.webm"
    text = transcribe_audio_bytes(raw, safe_name, language=language)
    return TranscribeResponse(text=text)


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


def _prepare_chat_turn(
    req: ChatRequest,
    mem: dict[str, Any],
    runtime: dict[str, Any],
):
    raw_history: list[dict[str, Any]] = []
    rolling_summary = ""
    if req.reset_context:
        if req.session_id:
            clear_rolling_summary(req.session_id, req.user_id)
    else:
        raw_history = _resolve_request_history(req, mem)
        if req.session_id and bool(mem.get("rolling_summary_enabled", True)):
            rolling_summary = get_rolling_summary(req.session_id, req.user_id)

    return prepare_turn(
        message=req.message,
        history=raw_history,
        memory_config=mem,
        llm_runtime=runtime,
        max_tokens_condense=req.max_tokens_rewrite,
        rolling_summary=rolling_summary,
        reset_context=bool(req.reset_context),
    )


def _resolve_chat_architecture(
    req: ChatRequest,
    mem: dict[str, Any],
    runtime: dict[str, Any],
    *,
    rag_override: str | None = None,
) -> tuple[str, str, str | None]:
    from agent.architecture_router import resolve_rag_architecture
    from agent.input_modes import resolve_input_mode
    from agent.llm_routing import routing_llm_runtime

    input_mode, doc_task_type = resolve_input_mode(
        input_mode=req.input_mode,
        doc_task_type=req.doc_task_type,
        temp_document_id=req.temp_document_id,
        message=req.message,
    )
    llm_rt = routing_llm_runtime(runtime)
    arch, _ = resolve_rag_architecture(
        req.message,
        department=req.user_department,
        input_mode=input_mode,
        doc_task_type=doc_task_type,
        scenario_tags=req.scenario_tags,
        request_override=rag_override or req.rag_architecture or mem.get("default_rag_architecture") or "auto",
        router_enabled=bool(mem.get("rag_arch_router_enabled", True)),
        llm_fallback=bool(mem.get("rag_arch_llm_fallback", False)),
        llm_runtime=llm_rt,
    )
    return arch, input_mode, doc_task_type


def _prepare_assistant_runtime(
    req: ChatRequest,
    base_mem: dict[str, Any],
) -> tuple[Any, bool, bool, dict[str, Any], str | None]:
    from agent.runtime.router import (
        apply_mode_to_memory,
        pick_hybrid_expert_mode,
        pick_rag_architecture_override,
        pick_stream_fast_mode,
        resolve_mode_profile,
    )

    ui = load_ui_config()
    profile = resolve_mode_profile(req.assistant_mode, ui)
    hybrid = pick_hybrid_expert_mode(profile, bool(ui.get("hybrid_expert_mode", False)))
    fast = pick_stream_fast_mode(
        profile,
        req.stream_fast_mode,
        bool(ui.get("stream_fast_mode", True)),
    )
    mem = apply_mode_to_memory(dict(base_mem), profile)
    mem = apply_routing_tier(apply_hybrid_expert_memory(mem, hybrid))
    rag_override = pick_rag_architecture_override(profile, req.rag_architecture)
    return profile, hybrid, fast, mem, rag_override


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, background_tasks: BackgroundTasks, request: Request):
    """步骤7：对话入口。"""
    runtime = resolve_llm_runtime(req)
    if not (runtime.get("llm_api_key") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="未配置 API Key：请在「模型配置」中保存密钥，或在 .env 中设置 OPENAI_API_KEY。",
        )
    base_mem = apply_department_chat_profile(
        _memory_for_user(request, req.user_id),
        req.user_department,
    )
    profile, _, _, mem, rag_override = _prepare_assistant_runtime(req, base_mem)
    turn = _prepare_chat_turn(req, mem, runtime)
    rag_arch, _, _ = _resolve_chat_architecture(req, mem, runtime, rag_override=rag_override)
    out = run_agent(
        question=turn.message,
        user_id=req.user_id,
        user_department=req.user_department,
        allowed_sources=req.allowed_sources,
        llm_runtime=runtime,
        history=turn.history_for_llm,
        memory_config=mem,
        retrieval_query=turn.retrieval_query,
        topic_shift=turn.topic_shift,
        skip_retrieval_rewrite=turn.skip_retrieval_rewrite,
        rolling_summary=turn.rolling_summary,
        rag_architecture=rag_arch,
    )
    if req.session_id and bool(mem.get("rolling_summary_enabled", True)):
        background_tasks.add_task(
            refresh_rolling_summary_for_session,
            req.session_id,
            req.user_id,
            mem,
            runtime,
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
def chat_stream(req: ChatRequest, request: Request):
    """SSE 流式对话：检索完成后逐 token 返回答案，末尾返回引用。"""
    import json
    import logging

    logger = logging.getLogger(__name__)

    def _sse_error_response(message: str) -> StreamingResponse:
        def _err_gen():
            payload = {"type": "error", "message": message[:400]}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            _err_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        runtime = resolve_llm_runtime(req)
        if not (runtime.get("llm_api_key") or "").strip():
            raise HTTPException(
                status_code=400,
                detail="未配置 API Key：请在「模型配置」中保存密钥，或在 .env 中设置 OPENAI_API_KEY。",
            )

        base_mem = apply_department_chat_profile(
            _memory_for_user(request, req.user_id),
            req.user_department,
        )
        profile, hybrid, fast, mem, rag_override = _prepare_assistant_runtime(req, base_mem)
        turn = _prepare_chat_turn(req, mem, runtime)
        history = turn.history_for_llm
        scenario_tags = list(req.scenario_tags or [])
        if req.channel and req.channel not in scenario_tags:
            scenario_tags.append(req.channel)
        state: dict[str, Any] = {
            "question": turn.message,
            "user_id": req.user_id,
            "user_department": req.user_department,
            "allowed_sources": req.allowed_sources,
            "history": history,
            "memory_config": mem,
            "retrieval_query": turn.retrieval_query,
            "topic_shift": turn.topic_shift,
            "skip_retrieval_rewrite": turn.skip_retrieval_rewrite,
            "rolling_summary": turn.rolling_summary,
            "turn_meta": turn.meta,
            "routing_model": runtime.get("routing_model"),
            "session_id": req.session_id,
            "quiet_routing": True,
            "hybrid_expert_mode": hybrid,
            "assistant_mode": profile.mode,
            "_assistant_force_tools": profile.force_tools,
            "llm_temperature_answer": req.temperature if req.temperature is not None else 0.2,
            "llm_max_tokens_rewrite": req.max_tokens_rewrite if req.max_tokens_rewrite is not None else 128,
            "llm_max_tokens_answer": req.max_tokens_answer,
            "llm_temperature_verifier": req.verifier_temperature,
            "llm_max_tokens_verifier": req.max_tokens_verifier,
            "rag_architecture": rag_override or req.rag_architecture,
            "input_mode": req.input_mode,
            "doc_task_type": req.doc_task_type,
            "temp_document_id": req.temp_document_id,
            "scenario_tags": scenario_tags or None,
            "channel": req.channel,
            "output_schema_id": req.output_schema_id,
            "skip_clarify": req.skip_clarify,
            "clarify_choice_id": req.clarify_choice_id,
        }
        state.update(
            build_stream_retrieval_state(
                fast,
                skip_query_rewrite=req.skip_query_rewrite,
            )
        )
        state.update(runtime)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("chat/stream failed before SSE generator")
        from api.stream_errors import format_stream_error

        return _sse_error_response(format_stream_error(exc))

    def _gen():
        from jnao_harness.availability import should_use_agent_lead
        from jnao_harness.lead_stream import stream_agent_lead

        try:
            if should_use_agent_lead(state):
                try:
                    yield from stream_agent_lead(state)
                    return
                except Exception as exc:
                    logger.warning(
                        "Jnao lead stream failed, falling back to KB path: %s",
                        exc,
                        exc_info=True,
                    )
            yield from stream_rag_chat(state)
        except Exception as exc:
            logger.exception("chat/stream generator failed")
            from api.stream_errors import format_stream_error

            payload = {"type": "error", "message": format_stream_error(exc)}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/chat/sessions", response_model=list[ChatSessionPublic])
def chat_sessions_list(request: Request, user_id: str = Query(..., min_length=1, max_length=128)):
    """按用户 ID 列出对话会话（SQLite 持久化）。"""
    tid = get_tenant_id(request)
    return [ChatSessionPublic.model_validate(s) for s in list_sessions(user_id, tenant_id=tid)]


@app.post("/chat/sessions", response_model=ChatSessionPublic)
def chat_sessions_create(req: ChatSessionCreate, request: Request):
    row = create_session(req.user_id, title=req.title, tenant_id=get_tenant_id(request))
    return ChatSessionPublic.model_validate(row)


@app.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessagePublic])
def chat_session_messages(
    request: Request,
    session_id: str,
    user_id: str = Query(..., min_length=1, max_length=128),
):
    tid = get_tenant_id(request)
    if not get_session(session_id, user_id, tenant_id=tid):
        raise HTTPException(status_code=404, detail="会话不存在")
    return [ChatMessagePublic.model_validate(m) for m in list_messages(session_id, user_id, tenant_id=tid)]


@app.post("/chat/sessions/{session_id}/messages", response_model=list[ChatMessagePublic])
def chat_session_append(session_id: str, req: ChatMessagesAppend, background_tasks: BackgroundTasks, request: Request):
    tid = get_tenant_id(request)
    if req.user_id.strip() != req.user_id:
        raise HTTPException(status_code=400, detail="invalid user_id")
    try:
        rows = append_messages(
            session_id,
            req.user_id,
            [m.model_dump(exclude_none=True) for m in req.messages],
            auto_title_from=req.auto_title_from,
            tenant_id=tid,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    mem = _memory_for_user(request, req.user_id)
    if bool(mem.get("rolling_summary_enabled", True)):
        background_tasks.add_task(
            refresh_rolling_summary_for_session,
            session_id,
            req.user_id,
            mem,
            None,
        )
    return [ChatMessagePublic.model_validate(m) for m in rows]


@app.put("/chat/sessions/{session_id}", response_model=ChatSessionPublic)
def chat_session_update(session_id: str, req: ChatSessionUpdate, request: Request):
    row = update_session_title(session_id, req.user_id, req.title, tenant_id=get_tenant_id(request))
    if not row:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ChatSessionPublic.model_validate(row)


@app.delete("/chat/sessions/{session_id}")
def chat_session_delete(
    request: Request,
    session_id: str,
    user_id: str = Query(..., min_length=1, max_length=128),
):
    if not delete_session(session_id, user_id, tenant_id=get_tenant_id(request)):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}


@app.get("/users/profile", response_model=UserProfilePublic)
def users_profile_get(request: Request, user_id: str = Query(..., min_length=1, max_length=128)):
    """读取用户资料（头像、昵称、部门）；不存在则创建默认记录。"""
    from auth.middleware import get_auth_user

    auth = get_auth_user(request)
    if auth and auth.get("id") != user_id.strip():
        raise HTTPException(status_code=403, detail="只能访问本人资料")
    row = get_user_profile(user_id)
    row = apply_auth_to_profile(row, auth)
    return UserProfilePublic.model_validate(row)


@app.put("/users/profile", response_model=UserProfilePublic)
def users_profile_update(req: UserProfileUpdate, request: Request):
    """更新用户资料（部门由账号绑定，不可自行修改）。"""
    from auth.middleware import get_auth_user

    auth = get_auth_user(request)
    if auth and auth.get("id") != req.user_id.strip():
        raise HTTPException(status_code=403, detail="只能修改本人资料")
    dept = auth["department"] if auth else req.department
    try:
        row = upsert_user_profile(
            req.user_id,
            display_name=req.display_name,
            avatar_url=req.avatar_url,
            department=dept,
            ai_display_name=req.ai_display_name,
            ai_avatar_url=req.ai_avatar_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if auth and req.display_name is not None:
        from auth.store import update_user_display_name

        update_user_display_name(auth["id"], req.display_name.strip())
        row = {**row, "display_name": req.display_name.strip()}
    return UserProfilePublic.model_validate(row)


@app.post("/users/profile/merge-legacy", response_model=UserProfilePublic)
def users_profile_merge_legacy(req: LegacyProfileMergeRequest, request: Request):
    """Merge pre-auth anonymous profile (avatar, nickname, sessions) into logged-in account."""
    from auth.middleware import get_auth_user

    auth = get_auth_user(request)
    if not auth:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        row = merge_legacy_user(req.legacy_user_id.strip(), auth["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    row = {**row, "department": auth["department"]}
    return UserProfilePublic.model_validate(row)


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


@app.post("/ingest/relationships", response_model=RelationshipImportResponse)
def ingest_relationships(req: RelationshipImportRequest):
    """结构化人物画像与关系入库，供对话中关系图工具展示。"""
    from graph.store import import_relationship_bundle

    people = [p.model_dump() for p in req.people]
    relationships = [r.model_dump() for r in req.relationships]
    pc, ec = import_relationship_bundle(
        source=req.source,
        department=req.department,
        people=people,
        relationships=relationships,
    )
    return RelationshipImportResponse(
        source=req.source,
        people_imported=pc,
        relationships_imported=ec,
        message=f"已导入 {pc} 个人物、{ec} 条关系",
    )


@app.post("/ingest/rebuild-relationships", response_model=RelationshipImportResponse)
def rebuild_relationships_from_source(
    source: str = Query(..., max_length=256, description="已入库文件的 source 名"),
    department: str | None = Query(default=None, max_length=64),
):
    """从已入库的 processed 文本重新解析组织关系图（无需重新向量入库）。"""
    from graph.org_chart import import_org_chart_if_detected

    processed = settings.data_processed_dir / Path(source).name
    if not processed.is_file():
        raise HTTPException(status_code=404, detail="未找到已入库文件，请先上传或检查 source 名称")
    text = processed.read_text(encoding="utf-8")
    dept = department or settings.default_department
    counts = import_org_chart_if_detected(text, source=source, department=dept)
    if not counts:
        raise HTTPException(
            status_code=422,
            detail="未能从该文件解析组织关系（需包含「姓名（职位）：向…汇报 / 管辖…」格式）",
        )
    pc, ec = counts
    return RelationshipImportResponse(
        source=source,
        people_imported=pc,
        relationships_imported=ec,
        message=f"已从 {source} 解析并导入 {pc} 个人物、{ec} 条关系",
    )


@app.post("/ingest/rebuild-domain-lexicon", response_model=DomainLexiconRebuildResponse)
def rebuild_domain_lexicon(
    replace: bool = Query(default=False, description="为 true 时清空后重建词表"),
    max_terms_per_doc: int = Query(default=80, ge=10, le=200),
):
    """从 data/raw（及 chunks jsonl）重建 domain_lexicon.json。"""
    from retrieval.domain_lexicon import rebuild_domain_lexicon_from_raw_dir

    stats = rebuild_domain_lexicon_from_raw_dir(replace=replace, max_terms_per_doc=max_terms_per_doc)
    path = settings.domain_lexicon_path
    return DomainLexiconRebuildResponse(
        term_count=int(stats.get("term_count") or 0),
        ingested_rows=int(stats.get("ingested_rows") or 0),
        updated_at=str(stats.get("updated_at") or ""),
        lexicon_path=str(path),
        message=f"已重建领域词表，共 {stats.get('term_count', 0)} 条术语",
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
        llm_runtime=llm_runtime,
    )
    result.ingest_mode = mode
    result.tools_used = proc.tools_used
    result.router = proc.router
    result.file_type = proc.file_type
    if result.chunks_indexed == 0:
        result.message = "文件已处理但未生成可索引片段，请检查内容是否过短。"
    return result


def _schedule_graph_extraction(
    parent_docs: list[dict[str, Any]],
    source: str,
    department: str,
    llm_runtime: dict[str, Any] | None = None,
) -> None:
    """Background graph extraction after ingest (non-blocking)."""
    import logging
    import threading

    from api.ui_config_store import load_ui_config

    if not load_ui_config().get("graph_extraction_enabled", True):
        return

    log = logging.getLogger(__name__)
    parents = [
        {
            "parent_id": p.get("parent_id"),
            "text": p.get("content") or p.get("text"),
            **p,
        }
        for p in parent_docs
    ]

    def _run() -> None:
        try:
            from graph.extract import extract_graph_from_parents

            extract_graph_from_parents(
                parents, source=source, department=department, llm_runtime=llm_runtime
            )
        except Exception:
            log.warning("graph extraction failed for %s", source, exc_info=True)

    threading.Thread(target=_run, daemon=True).start()


def _ingest_text(
    text: str,
    source: str,
    department: str | None = None,
    permission_label: str | None = None,
    tags: list[str] | None = None,
    llm_runtime: dict[str, Any] | None = None,
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

    def _finish(response: IngestResponse) -> IngestResponse:
        from retrieval.search_cache import invalidate_search_cache

        invalidate_search_cache()
        return response

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
    dept = department or settings.default_department
    if not children:
        graph_msg = ""
        try:
            from graph.org_chart import org_chart_ingest_message

            graph_msg = org_chart_ingest_message(text, source=source, department=dept)
        except Exception:
            import logging

            logging.getLogger(__name__).warning("org chart import failed for %s", source, exc_info=True)
        finalize_document_registry(
            source, text, parent_count=len(parents), child_count=0
        )
        return _finish(
            IngestResponse(
                chunks_indexed=0,
                source=source,
                tags=doc_tags,
                message=(dedup_stats.message or "") + graph_msg,
                dedup=IngestDedupStatsResponse(
                    content_hash=dedup_stats.content_hash or None,
                    skipped_parents=dedup_stats.skipped_parents,
                    skipped_children=dedup_stats.skipped_children,
                    indexed_parents=dedup_stats.indexed_parents,
                    indexed_children=0,
                ),
            )
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
        permission_labels=[c.permission_label for c in children],
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

    graph_msg = ""
    try:
        from graph.org_chart import org_chart_ingest_message

        graph_msg = org_chart_ingest_message(text, source=source, department=dept)
    except Exception:
        import logging

        logging.getLogger(__name__).warning("org chart import failed for %s", source, exc_info=True)

    _schedule_graph_extraction(parent_docs, source, dept, llm_runtime=llm_runtime)
    try:
        from retrieval.domain_lexicon import ingest_document_terms

        ingest_document_terms(text, source=source)
    except Exception:
        import logging

        logging.getLogger(__name__).warning("domain lexicon ingest failed for %s", source, exc_info=True)
    doc_rec = finalize_document_registry(
        source, text, parent_count=len(parents), child_count=len(children)
    )
    alias_sources = list(doc_rec.alias_sources) if doc_rec else dedup_stats.alias_sources
    return _finish(
        IngestResponse(
            chunks_indexed=len(children),
            source=source,
            tags=doc_tags,
            message=(dedup_stats.message or "") + graph_msg,
            dedup=IngestDedupStatsResponse(
                content_hash=dedup_stats.content_hash or None,
                skipped_parents=dedup_stats.skipped_parents,
                skipped_children=dedup_stats.skipped_children,
                indexed_parents=dedup_stats.indexed_parents,
                indexed_children=dedup_stats.indexed_children,
                alias_sources=alias_sources,
            ),
        )
    )
