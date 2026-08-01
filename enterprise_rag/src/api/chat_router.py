"""Chat HTTP routes — sessions, stream, uploads (extracted from api.main)."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from agent.conversation.rolling_summary import refresh_rolling_summary_for_session
from api.chat_identity import authenticated_chat_request, current_user_id, memory_for_user
from api.chat_service import prepare_assistant_runtime, prepare_chat_turn, resolve_chat_architecture
from api.chat_session_store import (
    append_messages,
    create_session,
    delete_session,
    get_session,
    list_messages,
    list_sessions,
    update_session_title,
)
from api.department_chat_profile import apply_department_chat_profile
from api.llm_resolve import resolve_llm_runtime
from api.schemas import (
    ChatMessagePublic,
    ChatMessagesAppend,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionPublic,
    ChatSessionUpdate,
    EphemeralDocPublic,
    SourceRef,
    TranscribeResponse,
)
from api.speech_transcribe import ALLOWED_CONTENT_TYPES, transcribe_audio_bytes
from api.stream_retrieval import build_stream_retrieval_state
from api.upload_utils import safe_upload_filename
from auth.middleware import get_auth_user
from config import settings
from tenant.context import get_tenant_id

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat/documents/upload", response_model=EphemeralDocPublic)
async def chat_document_upload(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Query(..., min_length=1, max_length=64),
):
    """Upload a temporary document for session-scoped Q&A (Classic RAG)."""
    from chat_ephemeral.store import save_ephemeral_document
    from document_loader.cleaner import clean_file

    user_id = current_user_id(request)
    tenant_id = get_tenant_id(request)
    if not get_session(session_id, user_id, tenant_id=tenant_id):
        raise HTTPException(status_code=404, detail="session not found")

    safe_name = safe_upload_filename(file.filename)
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
        department=str((get_auth_user(request) or {}).get("department") or ""),
    )
    return EphemeralDocPublic(doc_id=doc.doc_id, filename=doc.filename, session_id=doc.session_id)


@router.post("/chat/transcribe", response_model=TranscribeResponse)
async def chat_transcribe(
    file: UploadFile = File(...),
    language: str = Query(default="zh", max_length=16),
):
    """Upload short audio and transcribe via Whisper (fallback when browser speech API unavailable)."""
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="不支持的音频格式")
    raw = await file.read()
    safe_name = safe_upload_filename(file.filename) or "speech.webm"
    text = transcribe_audio_bytes(raw, safe_name, language=language)
    return TranscribeResponse(text=text)


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, background_tasks: BackgroundTasks, request: Request):
    """步骤7：对话入口。"""
    from agent.graph import run_agent

    req = authenticated_chat_request(req, request)
    runtime = resolve_llm_runtime(req)
    if not (runtime.get("llm_api_key") or "").strip():
        raise HTTPException(
            status_code=400,
            detail="未配置 API Key：请在「模型配置」中保存密钥，或在 .env 中设置 OPENAI_API_KEY。",
        )
    base_mem = apply_department_chat_profile(
        memory_for_user(request, req.user_id),
        req.user_department,
    )
    profile, _, _, mem, rag_override = prepare_assistant_runtime(req, base_mem)
    turn = prepare_chat_turn(req, mem, runtime)
    rag_arch, _, _ = resolve_chat_architecture(req, mem, runtime, rag_override=rag_override)
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


@router.post("/chat/stream")
def chat_stream(req: ChatRequest, request: Request):
    """SSE 流式对话：检索完成后逐 token 返回答案，末尾返回引用。"""
    req = authenticated_chat_request(req, request)

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
            memory_for_user(request, req.user_id),
            req.user_department,
        )
        profile, hybrid, fast, mem, rag_override = prepare_assistant_runtime(req, base_mem)
        turn = prepare_chat_turn(req, mem, runtime)
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
        from jnao_harness.availability import resolve_chat_pipeline, stream_chat_events

        try:
            yield from stream_chat_events(state)
        except Exception as exc:
            logger.exception("chat/stream generator failed")
            from api.stream_errors import format_stream_error

            payload = {"type": "error", "message": format_stream_error(exc)}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    from jnao_harness.availability import resolve_chat_pipeline

    pipeline = resolve_chat_pipeline(state)
    logger.debug("chat/stream pipeline=%s assistant_mode=%s", pipeline, state.get("assistant_mode"))

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions", response_model=list[ChatSessionPublic])
def chat_sessions_list(request: Request):
    """按用户 ID 列出对话会话（SQLite 持久化）。"""
    tid = get_tenant_id(request)
    user_id = current_user_id(request)
    return [ChatSessionPublic.model_validate(s) for s in list_sessions(user_id, tenant_id=tid)]


@router.post("/chat/sessions", response_model=ChatSessionPublic)
def chat_sessions_create(req: ChatSessionCreate, request: Request):
    row = create_session(current_user_id(request), title=req.title, tenant_id=get_tenant_id(request))
    return ChatSessionPublic.model_validate(row)


@router.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessagePublic])
def chat_session_messages(
    request: Request,
    session_id: str,
):
    tid = get_tenant_id(request)
    user_id = current_user_id(request)
    if not get_session(session_id, user_id, tenant_id=tid):
        raise HTTPException(status_code=404, detail="会话不存在")
    return [ChatMessagePublic.model_validate(m) for m in list_messages(session_id, user_id, tenant_id=tid)]


@router.post("/chat/sessions/{session_id}/messages", response_model=list[ChatMessagePublic])
def chat_session_append(session_id: str, req: ChatMessagesAppend, background_tasks: BackgroundTasks, request: Request):
    tid = get_tenant_id(request)
    user_id = current_user_id(request)
    try:
        rows = append_messages(
            session_id,
            user_id,
            [m.model_dump(exclude_none=True) for m in req.messages],
            auto_title_from=req.auto_title_from,
            tenant_id=tid,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    mem = memory_for_user(request, user_id)
    if bool(mem.get("rolling_summary_enabled", True)):
        background_tasks.add_task(
            refresh_rolling_summary_for_session,
            session_id,
            user_id,
            mem,
            None,
        )
    return [ChatMessagePublic.model_validate(m) for m in rows]


@router.put("/chat/sessions/{session_id}", response_model=ChatSessionPublic)
def chat_session_update(session_id: str, req: ChatSessionUpdate, request: Request):
    row = update_session_title(
        session_id,
        current_user_id(request),
        req.title,
        tenant_id=get_tenant_id(request),
    )
    if not row:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ChatSessionPublic.model_validate(row)


@router.delete("/chat/sessions/{session_id}")
def chat_session_delete(
    request: Request,
    session_id: str,
):
    if not delete_session(session_id, current_user_id(request), tenant_id=get_tenant_id(request)):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
