"""TDD: robust LLM JSON extract + detailed ingest errors (chat works but parse fails)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_extract_json_strips_markdown_fence():
    from exam_bank.llm_ingest import _extract_json

    raw = """```json
{"answers_embedded": true, "items": [{"question_no": "1", "stem": "x", "qtype": "choice", "is_question": true}]}
```"""
    data = _extract_json(raw)
    assert data is not None
    assert data["answers_embedded"] is True
    assert len(data["items"]) == 1


def test_extract_items_uses_chat_model_not_routing(monkeypatch):
    from exam_bank import llm_ingest
    import exam_bank.llm_client as lc

    captured: dict = {}

    class _Msg:
        content = '{"answers_embedded":false,"items":[{"question_no":"1","qtype":"choice","stem":"1+1","options":["A.1","B.2"],"answer":"B","analysis":"","knowledge_tags":["运算"],"difficulty":1,"is_question":true}]}'

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
                "model": "routing-small",
                "chat_model": "deepseek-v4-flash",
                "llm_api_base": "https://api.deepseek.com/v1",
                "source": "env",
            },
        ),
    )

    out = llm_ingest.extract_items_with_llm("1. 1+1\nA.1\nB.2", subject="数学", grade="初一")
    assert out is not None
    assert out.get("items")
    assert captured.get("model") == "deepseek-v4-flash"


def test_extract_items_surfaces_api_error(monkeypatch):
    from exam_bank import llm_ingest
    import exam_bank.llm_client as lc

    class _Completions:
        def create(self, **kwargs):
            raise RuntimeError("model_not_found: deepseek-v3-flash")

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
                "model": "deepseek-v3-flash",
                "chat_model": "deepseek-v3-flash",
                "llm_api_base": "https://api.deepseek.com/v1",
                "source": "env",
            },
        ),
    )

    out = llm_ingest.extract_items_with_llm("1. x", subject="数学")
    assert out is not None
    assert out.get("items") == []
    assert out.get("error") == "llm_api_error"
    assert "model_not_found" in (out.get("message") or "")


def test_parse_paper_items_passes_detailed_error(monkeypatch):
    from exam_bank import item_split, llm_ingest

    monkeypatch.setattr(
        llm_ingest,
        "extract_items_with_llm",
        lambda *a, **k: {
            "items": [],
            "item_count": 0,
            "error": "llm_api_error",
            "message": "上游返回 429 限流，请稍后重试",
            "router": "llm_failed",
        },
    )
    out = item_split.parse_paper_items("试卷", subject="数学", use_llm=True)
    assert out["error"] == "llm_api_error"
    assert "429" in out["message"]
