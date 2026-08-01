"""Tests for chat pipeline routing (DeerFlow lead vs KB fast path)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _reset_lead_flag(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "chat_lead_agent_enabled", True)


def test_knowledge_mode_uses_kb_fast_path(monkeypatch):
    from jnao_harness import availability

    monkeypatch.setattr(availability, "harness_available", lambda: True)
    state = {"assistant_mode": "knowledge"}
    assert availability.resolve_chat_pipeline(state) == "kb_fast"
    assert availability.should_use_agent_lead(state) is False


def test_task_mode_uses_lead_when_harness_present(monkeypatch):
    from jnao_harness import availability

    monkeypatch.setattr(availability, "harness_available", lambda: True)
    state = {"assistant_mode": "task"}
    assert availability.resolve_chat_pipeline(state) == "lead_agent"
    assert availability.should_use_agent_lead(state) is True


def test_lead_disabled_falls_back_to_kb(monkeypatch):
    from config import settings
    from jnao_harness import availability

    monkeypatch.setattr(settings, "chat_lead_agent_enabled", False)
    monkeypatch.setattr(availability, "harness_available", lambda: True)
    state = {"assistant_mode": "task"}
    assert availability.resolve_chat_pipeline(state) == "kb_fast"


def test_chat_stream_endpoint_resolves_pipeline_without_500(monkeypatch):
    """Regression: resolve_chat_pipeline must be in scope before StreamingResponse."""
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.chat_router import router as chat_router
    from jnao_harness import availability

    def _fake_stream(_state):
        yield 'data: {"type":"done","answer":"ok"}\n\n'

    monkeypatch.setattr(availability, "stream_chat_events", _fake_stream)
    monkeypatch.setattr(
        "api.chat_router.resolve_llm_runtime",
        lambda _req: {"llm_api_key": "sk-test", "chat_model": "test-model"},
    )
    monkeypatch.setattr(
        "api.chat_router.prepare_assistant_runtime",
        lambda req, mem: (
            type("P", (), {"mode": req.assistant_mode or "task"})(),
            False,
            True,
            mem,
            None,
        ),
    )
    monkeypatch.setattr(
        "api.chat_router.prepare_chat_turn",
        lambda req, mem, runtime: type(
            "T",
            (),
            {
                "message": req.message,
                "history_for_llm": [],
                "retrieval_query": req.message,
                "topic_shift": False,
                "skip_retrieval_rewrite": True,
                "rolling_summary": "",
                "meta": {},
            },
        )(),
    )
    monkeypatch.setattr("api.chat_router.build_stream_retrieval_state", lambda *a, **k: {})
    monkeypatch.setattr("api.chat_router.memory_for_user", lambda *a, **k: {})
    monkeypatch.setattr("api.chat_router.apply_department_chat_profile", lambda mem, _d: mem)

    app = FastAPI()
    app.include_router(chat_router)
    auth = {"id": "u1", "username": "tech1", "department": "技术部"}

    with patch("api.chat_identity.get_auth_user", return_value=auth):
        client = TestClient(app)
        r = client.post(
            "/chat/stream",
            json={
                "message": "今天天气如何",
                "assistant_mode": "task",
                "history": [],
                "stream_fast_mode": True,
                "skip_query_rewrite": True,
            },
        )
    assert r.status_code == 200, r.text
    assert "text/event-stream" in (r.headers.get("content-type") or "")
