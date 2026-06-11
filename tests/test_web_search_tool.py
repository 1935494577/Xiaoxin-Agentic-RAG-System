"""Tests for Tavily web search agent tool."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.tools.builtins.web_search import web_search  # noqa: E402
from agent.tools.config.registry import TOOL_DEFINITIONS, execute_tool  # noqa: E402
from config import settings  # noqa: E402


def test_web_search_requires_query():
    assert "请提供" in web_search("")


def test_web_search_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "")
    out = web_search("2026年春节放假安排")
    assert "TAVILY_API_KEY" in out


def test_web_search_formats_tavily_response(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")
    monkeypatch.setattr(settings, "web_search_max_results", 3)
    fake = {
        "answer": "2026年春节放假7天。",
        "results": [
            {
                "title": "国务院通知",
                "url": "https://example.gov.cn/holiday",
                "content": "2026年1月28日至2月3日放假调休。",
            },
            {
                "title": "日历解读",
                "url": "https://example.com/calendar",
                "content": "含调休上班日期说明。",
            },
        ],
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = fake

    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp

    with patch("agent.tools.builtins.web_search.httpx.Client", return_value=mock_client):
        out = web_search("2026年春节放假安排")

    assert "2026年春节放假7天" in out
    assert "国务院通知" in out
    assert "example.gov.cn" in out
    mock_client.post.assert_called_once()
    body = mock_client.post.call_args.kwargs["json"]
    assert body["query"] == "2026年春节放假安排"
    assert body["api_key"] == "tvly-test"


def test_registry_includes_web_search():
    assert "web_search" in TOOL_DEFINITIONS


def test_execute_tool_web_search(monkeypatch):
    import agent.tools.builtins as builtins_mod

    def fake_search(query: str, max_results: int | None = None) -> str:
        return f"mock:{query}"

    monkeypatch.setattr(builtins_mod, "web_search", fake_search)
    out = execute_tool("web_search", {"query": "北京时间"})
    assert out == "mock:北京时间"
