"""Exam LLM client reuses .env / default profile."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_ensure_deepseek_v1_suffix():
    from exam_bank.llm_client import _ensure_openai_compatible_base

    assert _ensure_openai_compatible_base("https://api.deepseek.com") == "https://api.deepseek.com/v1"
    assert _ensure_openai_compatible_base("https://api.deepseek.com/v1") == "https://api.deepseek.com/v1"


def test_resolve_exam_llm_uses_settings_model(monkeypatch):
    from config import settings
    from exam_bank import llm_client

    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_api_base", "https://api.deepseek.com")
    monkeypatch.setattr(settings, "openai_chat_model", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "openai_routing_model", "")

    # Force env path (ignore profiles)
    monkeypatch.setattr(
        llm_client,
        "resolve_exam_llm_runtime",
        lambda: {
            "llm_api_base": llm_client._ensure_openai_compatible_base(settings.openai_api_base),
            "llm_api_key": settings.openai_api_key,
            "chat_model": settings.openai_chat_model,
            "routing_model": settings.openai_chat_model,
            "model": settings.openai_chat_model,
            "llm_extra_headers": {},
            "source": "env",
        },
    )
    rt = llm_client.resolve_exam_llm_runtime()
    assert rt["model"] == "deepseek-v4-flash"
    assert rt["llm_api_base"].endswith("/v1")


def test_route_paper_passes_deepseek_model(monkeypatch):
    from exam_bank import paper_router
    import exam_bank.llm_client as lc

    captured: dict = {}

    class _Msg:
        content = '{"subject":"数学","grade":"初二","stage":"junior","sections":[{"heading":"一、选择题","qtype":"choice","approx_count":5}],"confidence":0.9}'

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    monkeypatch.setattr(
        lc,
        "build_openai_client",
        lambda **kw: (
            _Client(),
            {
                "model": "deepseek-v4-flash",
                "llm_api_base": "https://api.deepseek.com/v1",
                "source": "env",
            },
        ),
    )

    out = paper_router.route_paper_with_llm("一、选择题\n1.x")
    assert out is not None
    assert out["model"] == "deepseek-v4-flash"
    assert captured.get("model") == "deepseek-v4-flash"
