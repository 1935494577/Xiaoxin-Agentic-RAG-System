"""IM channel → Main RAG API (knowledge mode) bridge."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT_SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))


def test_build_chat_payload_forces_knowledge_mode():
    from app.channels.message_bus import InboundMessage, InboundMessageType
    from jnao_harness.channel_rag_backend import build_chat_payload, im_session_id

    msg = InboundMessage(
        channel_name="wecom",
        chat_id="chat-1",
        user_id="wx-user",
        text="你好",
        msg_type=InboundMessageType.CHAT,
    )
    payload = build_chat_payload(msg)
    assert payload["assistant_mode"] == "knowledge"
    assert payload["channel"] == "wecom"
    assert payload["message"] == "你好"
    assert payload["session_id"] == im_session_id(msg)
    assert payload["skip_clarify"] is True


def test_unbound_wecom_user_gets_im_default_department():
    from app.channels.message_bus import InboundMessage, InboundMessageType
    from jnao_harness.channel_rag_backend import _department_for_im_header, _request_headers, build_chat_payload

    msg = InboundMessage(
        channel_name="wecom",
        chat_id="group-1",
        user_id="tianlu",
        text="测试",
        msg_type=InboundMessageType.CHAT,
        topic_id="tianlu",
    )
    payload = build_chat_payload(msg, im_default_department="技术部")
    assert payload["user_department"] == "技术部"
    assert payload["user_id"].startswith("im-wecom-")
    assert _department_for_im_header("技术部") == "general"
    headers = _request_headers(payload)
    headers["X-IM-User-Department"].encode("latin-1")


def test_resolve_wecom_group_chat_id():
    from app.channels.wecom import _resolve_wecom_chat_id

    body = {"chattype": "group", "chatid": "wrOxxxxxxxx"}
    assert _resolve_wecom_chat_id(body, "user1") == "wrOxxxxxxxx"
    assert _resolve_wecom_chat_id({"chattype": "single"}, "user1") == "user1"


def test_parse_sse_line():
    from jnao_harness.channel_rag_backend import _parse_sse_line

    event = _parse_sse_line('data: {"type":"token","content":"你"}')
    assert event == {"type": "token", "content": "你"}
    assert _parse_sse_line("not-data") is None


def test_iter_rag_stream_events_parses_tokens():
    import asyncio

    from jnao_harness.channel_rag_backend import iter_rag_stream_events

    class FakeResponse:
        status_code = 200

        async def aread(self):
            return b""

        async def aiter_text(self):
            yield 'data: {"type":"token","content":"劲脑"}\n\n'
            yield 'data: {"type":"done","answer":"劲脑知识库回答"}\n\n'

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class FakeClient:
        def stream(self, *args, **kwargs):
            return FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    import jnao_harness.channel_rag_backend as mod

    original = mod.httpx.AsyncClient
    mod.httpx.AsyncClient = lambda *a, **k: FakeClient()
    try:

        async def _collect():
            return [e async for e in mod.iter_rag_stream_events({"message": "x"}, api_base="http://test")]

        events = asyncio.run(_collect())
    finally:
        mod.httpx.AsyncClient = original

    assert events[0]["type"] == "token"
    assert events[1]["answer"] == "劲脑知识库回答"


def test_rag_backend_enabled_defaults_on():
    from jnao_harness.channel_rag_backend import rag_backend_enabled, resolve_rag_api_url

    assert rag_backend_enabled(config_flag=True) is True
    assert resolve_rag_api_url("http://127.0.0.1:8010") == "http://127.0.0.1:8010"
