"""Tests for ReefAPI agent tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.tools.builtins.reefapi import reefapi_call, reefapi_search  # noqa: E402
from agent.tools.config.registry import TOOL_DEFINITIONS, execute_tool  # noqa: E402
from config import settings  # noqa: E402


def _catalog_fixture() -> dict:
    return {
        "engine_count": 2,
        "engines": [
            {
                "name": "amazon",
                "title": "Amazon product data",
                "category": {"title": "E-commerce"},
                "actions": [
                    {
                        "name": "offers",
                        "description": "Buy box and offers by ASIN",
                        "required_params": ["asin"],
                        "optional_params": ["domain"],
                        "example_params": {"asin": "B0C123", "domain": "com"},
                    }
                ],
            },
            {
                "name": "reddit",
                "title": "Reddit posts and comments",
                "category": {"title": "Social"},
                "actions": [
                    {
                        "name": "search_comments",
                        "description": "Search comments",
                        "required_params": ["query"],
                        "optional_params": ["limit"],
                    }
                ],
            },
        ],
    }


def test_registry_includes_reefapi_tools():
    assert "reefapi_search" in TOOL_DEFINITIONS
    assert "reefapi_call" in TOOL_DEFINITIONS


def test_reefapi_call_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "reefapi_key", "")
    out = reefapi_call("amazon", "offers", {"asin": "B0C"})
    assert "REEFAPI_KEY" in out


def test_reefapi_search_ranks_engines(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _catalog_fixture()
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("agent.tools.builtins.reefapi.httpx.Client", return_value=mock_client):
        out = reefapi_search(query="amazon offers")

    data = json.loads(out)
    assert data["count"] >= 1
    assert data["engines"][0]["engine"] == "amazon"


def test_reefapi_search_engine_detail(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _catalog_fixture()
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("agent.tools.builtins.reefapi.httpx.Client", return_value=mock_client):
        out = reefapi_search(engine="reddit")

    data = json.loads(out)
    assert data["engine"] == "reddit"
    assert data["actions"][0]["action"] == "search_comments"


def test_reefapi_call_posts_json(monkeypatch):
    monkeypatch.setattr(settings, "reefapi_key", "ak_live_test")
    fake = {"ok": True, "data": {"asin": "B0C"}, "meta": {"credits": 1}, "error": None}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp

    with patch("agent.tools.builtins.reefapi.httpx.Client", return_value=mock_client):
        out = reefapi_call("amazon", "offers", {"asin": "B0C", "domain": "com"})

    data = json.loads(out)
    assert data["ok"] is True
    mock_client.post.assert_called_once()
    assert mock_client.post.call_args.args[0] == "/amazon/v1/offers"
    assert mock_client.post.call_args.kwargs["json"]["asin"] == "B0C"


def test_execute_tool_reefapi_search(monkeypatch):
    import agent.tools.builtins as builtins_mod

    def fake_search(*, query: str = "", engine: str = "") -> str:
        return json.dumps({"query": query, "engine": engine})

    monkeypatch.setattr(builtins_mod, "reefapi_search", fake_search)
    out = execute_tool("reefapi_search", {"query": "domain"})
    assert "domain" in out
