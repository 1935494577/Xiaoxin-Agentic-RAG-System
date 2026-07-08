"""Route IM channel messages to Main RAG API (/chat/stream, knowledge mode)."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.channels.message_bus import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)

_DEFAULT_RAG_API_URL = "http://127.0.0.1:8010"
_STREAM_MIN_INTERVAL = 1.0
_STREAM_MIN_CHARS = 60


def resolve_rag_api_url(explicit: str | None = None) -> str:
    if explicit and str(explicit).strip():
        return str(explicit).strip().rstrip("/")
    for key in ("JNAO_CHANNEL_RAG_API_URL", "JNAO_MAIN_API_URL"):
        value = os.environ.get(key, "").strip().rstrip("/")
        if value:
            return value
    return _DEFAULT_RAG_API_URL


def rag_backend_enabled(*, config_flag: bool | None = None) -> bool:
    if config_flag is not None:
        return bool(config_flag)
    raw = os.environ.get("JNAO_CHANNEL_RAG_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def im_session_id(msg: InboundMessage) -> str:
    import hashlib

    raw = f"{msg.channel_name}:{msg.chat_id}:{msg.topic_id or ''}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:28]
    return f"im-{msg.channel_name[:6]}-{digest}"[:64]


def resolve_im_department(*, manager_default: str | None = None) -> str:
    """Department for IM KB ACL (default 技术部 so group members see internal+public docs)."""
    if manager_default and str(manager_default).strip():
        return str(manager_default).strip()
    for key in ("JNAO_IM_DEFAULT_DEPARTMENT",):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    try:
        from config import settings

        return str(settings.default_department or "技术部")
    except Exception:
        return "技术部"


def resolve_jnao_user(
    msg: InboundMessage,
    *,
    im_default_department: str | None = None,
) -> tuple[str, str]:
    owner_id = getattr(msg, "owner_user_id", None) or None
    if not owner_id:
        try:
            from app.gateway.auth_disabled import AUTH_DISABLED_USER_ID, is_auth_disabled

            if is_auth_disabled():
                owner_id = AUTH_DISABLED_USER_ID
        except ImportError:
            owner_id = None
    if owner_id:
        try:
            from auth.store import get_user_by_id

            row = get_user_by_id(str(owner_id))
            if row:
                dept = str(row.get("department") or im_default_department or resolve_im_department())
                return str(row["id"]), dept
        except Exception:
            logger.debug("Failed to resolve bound owner profile", exc_info=True)
        return str(owner_id), resolve_im_department(manager_default=im_default_department)
    platform_uid = f"im-{msg.channel_name}-{msg.user_id or 'anon'}"[:128]
    return platform_uid, resolve_im_department(manager_default=im_default_department)


def build_chat_payload(msg: InboundMessage, *, im_default_department: str | None = None) -> dict[str, Any]:
    user_id, user_department = resolve_jnao_user(msg, im_default_department=im_default_department)
    channel_tag = msg.channel_name if msg.channel_name in {"wecom", "wechat", "miniprogram", "channels", "douyin"} else None
    return {
        "message": (msg.text or "").strip(),
        "user_id": user_id,
        "user_department": user_department,
        "session_id": im_session_id(msg),
        "assistant_mode": "knowledge",
        "channel": channel_tag,
        "skip_clarify": True,
        "scenario_tags": [f"im:{msg.channel_name}"],
    }


def _department_for_im_header(department: str | None) -> str:
    """HTTP headers must be latin-1; map 技术部 → general (body keeps canonical dept)."""
    dept = (department or "").strip()
    if not dept:
        return "general"
    try:
        dept.encode("latin-1")
        return dept
    except UnicodeEncodeError:
        pass
    from security.access_control import _LEGACY_DEPARTMENT_ALIASES

    for alias, canonical in _LEGACY_DEPARTMENT_ALIASES.items():
        if canonical == dept:
            return alias
    return "general"


def _request_headers(payload: dict[str, Any]) -> dict[str, str]:
    user_dept = str(payload.get("user_department") or resolve_im_department())
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "X-IM-Internal": "1",
        "X-IM-User-Id": str(payload.get("user_id") or ""),
        "X-IM-User-Department": _department_for_im_header(user_dept),
    }
    try:
        from config import settings

        secret = (settings.rag_api_secret or "").strip()
        if secret:
            headers["X-API-Key"] = secret
    except Exception:
        pass
    return headers


def _parse_sse_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped.startswith("data:"):
        return None
    payload = stripped[5:].strip()
    if not payload:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


async def iter_rag_stream_events(
    payload: dict[str, Any],
    *,
    api_base: str,
    timeout: float = 180.0,
) -> AsyncIterator[dict[str, Any]]:
    url = f"{api_base.rstrip('/')}/chat/stream"
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload, headers=_request_headers(payload)) as response:
            if response.status_code >= 400:
                body = await response.aread()
                detail = body.decode("utf-8", errors="replace")[:400]
                yield {"type": "error", "message": detail or f"HTTP {response.status_code}"}
                return
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    event = _parse_sse_line(line)
                    if event:
                        yield event


async def ensure_im_session(user_id: str, session_id: str) -> None:
    import asyncio

    def _ensure() -> None:
        from api.chat_session_store import ensure_chat_session, init_chat_session_db

        init_chat_session_db()
        ensure_chat_session(session_id, user_id, title="IM 对话")

    await asyncio.to_thread(_ensure)


async def persist_im_turn(user_id: str, session_id: str, user_text: str, assistant_text: str) -> None:
    import asyncio

    def _append() -> None:
        from api.chat_session_store import append_messages, init_chat_session_db

        init_chat_session_db()
        append_messages(
            session_id,
            user_id,
            [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_text},
            ],
        )

    try:
        await asyncio.to_thread(_append)
    except Exception:
        logger.warning("Failed to persist IM chat turn session=%s user=%s", session_id, user_id, exc_info=True)


async def handle_channel_rag_chat(manager: Any, msg: InboundMessage) -> bool:
    """Stream or wait for Main API RAG answer and publish outbound IM messages."""
    from app.channels.message_bus import InboundMessageType

    if not getattr(manager, "_use_rag_backend", False):
        return False
    if msg.msg_type != InboundMessageType.CHAT:
        return False

    api_base = resolve_rag_api_url(getattr(manager, "_rag_api_url", None))
    im_dept = getattr(manager, "_im_default_department", None)
    payload = build_chat_payload(msg, im_default_department=im_dept)
    if not payload["message"]:
        return False

    user_id = payload["user_id"]
    session_id = payload["session_id"]
    await ensure_im_session(user_id, session_id)

    from app.channels.manager import (
        STREAM_UPDATE_MIN_CHARS,
        STREAM_UPDATE_MIN_INTERVAL_SECONDS,
        _response_metadata,
    )

    supports_streaming = manager._channel_supports_streaming(msg.channel_name)
    thread_id = session_id
    latest_text = ""
    last_published = ""
    last_published_len = 0
    last_publish_at = 0.0
    stream_error: str | None = None

    try:
        async for event in iter_rag_stream_events(payload, api_base=api_base):
            etype = event.get("type")
            if etype == "error":
                stream_error = str(event.get("message") or "RAG 请求失败")
                break
            if etype == "token":
                delta = str(event.get("content") or "")
                if delta:
                    latest_text += delta
            elif etype == "done":
                answer = str(event.get("answer") or "").strip()
                if answer:
                    latest_text = answer
                break
            if not supports_streaming or not latest_text or latest_text == last_published:
                continue
            now = time.monotonic()
            new_chars = len(latest_text) - last_published_len
            if last_published and now - last_publish_at < STREAM_UPDATE_MIN_INTERVAL_SECONDS and new_chars < STREAM_UPDATE_MIN_CHARS:
                continue
            await manager.bus.publish_outbound(
                OutboundMessage(
                    channel_name=msg.channel_name,
                    chat_id=msg.chat_id,
                    thread_id=thread_id,
                    text=latest_text + " ▉",
                    is_final=False,
                    thread_ts=msg.thread_ts,
                    connection_id=msg.connection_id,
                    owner_user_id=msg.owner_user_id,
                    metadata=_response_metadata(msg.metadata),
                )
            )
            last_published = latest_text
            last_published_len = len(latest_text)
            last_publish_at = now
    except Exception as exc:
        logger.exception("[RAG backend] IM chat failed")
        stream_error = str(exc)

    response_text = latest_text.strip()
    if stream_error and not response_text:
        response_text = stream_error[:400]
    if not response_text:
        response_text = "暂时无法生成回答，请稍后再试。"

    await persist_im_turn(user_id, session_id, payload["message"], response_text)

    await manager.bus.publish_outbound(
        OutboundMessage(
            channel_name=msg.channel_name,
            chat_id=msg.chat_id,
            thread_id=thread_id,
            text=response_text,
            is_final=True,
            thread_ts=msg.thread_ts,
            connection_id=msg.connection_id,
            owner_user_id=msg.owner_user_id,
            metadata=_response_metadata(msg.metadata),
        )
    )
    logger.info(
        "[RAG backend] IM reply sent channel=%s chat_id=%s len=%d",
        msg.channel_name,
        msg.chat_id,
        len(response_text),
    )
    return True
