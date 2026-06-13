"""Routing model and latency tier tests."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.llm_routing import model_for_task, routing_llm_runtime  # noqa: E402
from api.chat_routing import apply_routing_tier  # noqa: E402
from api.llm_resolve import resolve_llm_runtime  # noqa: E402
from api.schemas import ChatRequest  # noqa: E402


def test_model_for_task_prefers_routing_model():
    rt = {"chat_model": "gpt-4o", "routing_model": "gpt-4o-mini"}
    assert model_for_task(rt, task="routing") == "gpt-4o-mini"
    assert model_for_task(rt, task="answer") == "gpt-4o"


def test_routing_llm_runtime_swaps_chat_model():
    rt = {"chat_model": "big", "routing_model": "small", "llm_api_key": "k"}
    out = routing_llm_runtime(rt)
    assert out["chat_model"] == "small"
    assert out["routing_model"] == "small"


def test_apply_routing_tier_fast():
    mem = apply_routing_tier({"chat_routing_tier": "fast", "kb_llm_judge": True})
    assert mem["condense_llm_enabled"] is False
    assert mem["kb_llm_judge"] is False


def test_apply_routing_tier_quality():
    mem = apply_routing_tier({"chat_routing_tier": "quality"})
    assert mem["kb_llm_judge_always"] is True


def test_resolve_llm_runtime_routing_from_request(monkeypatch):
    monkeypatch.setattr(
        "api.llm_resolve.load_ui_config",
        lambda: {"routing_model": "ui-mini"},
    )
    req = ChatRequest(
        message="hi",
        user_id="u1",
        force_env_llm=True,
        chat_model="answer-big",
        routing_model="req-mini",
    )
    rt = resolve_llm_runtime(req)
    assert rt["chat_model"] == "answer-big"
    assert rt["routing_model"] == "req-mini"
