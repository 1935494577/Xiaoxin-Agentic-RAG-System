"""TDD: web_search freshness (days) + authoritative domains for typhoon/news."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.tools.builtins.web_search import (  # noqa: E402
    looks_like_timeliness_query,
    web_search,
)
from agent.tools.builtins import run_builtin  # noqa: E402
from config import settings  # noqa: E402


def test_looks_like_timeliness_query_detects_typhoon():
    assert looks_like_timeliness_query("台风白海豚最新路径")
    assert looks_like_timeliness_query("中央气象台预警")
    assert not looks_like_timeliness_query("Python 列表推导式怎么写")


def test_web_search_auto_applies_days_and_domains_for_typhoon(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")
    monkeypatch.setattr(settings, "web_search_max_results", 5)

    fake = {
        "answer": "台风白海豚正在东海活动。",
        "results": [
            {
                "title": "中央气象台",
                "url": "https://www.nmc.cn/typhoon",
                "content": "今年第几号台风白海豚…",
                "published_date": "2026-08-07",
            },
            {
                "title": "旧闻巴威",
                "url": "https://example.com/old",
                "content": "台风巴威已登陆浙江",
                "published_date": "2020-08-01",
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
        out = web_search("台风白海豚 最新路径 萧山")

    body = mock_client.post.call_args.kwargs["json"]
    assert body.get("days") == 3
    domains = body.get("include_domains") or []
    assert "nmc.cn" in domains or "weather.com.cn" in domains
    assert "白海豚" in out
    # 过旧结果应被过滤或标注
    assert "2020-08-01" not in out or "可能过时" in out


def test_web_search_explicit_days_overrides_auto(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"answer": "ok", "results": []}
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp

    with patch("agent.tools.builtins.web_search.httpx.Client", return_value=mock_client):
        web_search("今日新闻", days=7)

    body = mock_client.post.call_args.kwargs["json"]
    assert body.get("days") == 7


def test_run_builtin_passes_days(monkeypatch):
    import agent.tools.builtins as builtins_mod

    seen: dict = {}

    def fake_search(query: str, max_results: int | None = None, days: int | None = None, include_domains=None) -> str:
        seen["days"] = days
        seen["query"] = query
        return "ok"

    monkeypatch.setattr(builtins_mod, "web_search", fake_search)
    out = run_builtin("web_search", {"query": "台风白海豚", "days": 3})
    assert out == "ok"
    assert seen["days"] == 3
