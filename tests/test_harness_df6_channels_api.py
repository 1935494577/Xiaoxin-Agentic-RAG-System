"""DF-6: /api/channels/ must register without deerflow (main .venv)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))


def test_channels_router_importable_without_deerflow():
    pytest.importorskip("fastapi")
    from jnao_harness.gateway.routers.channels import router as channels_router

    assert channels_router.prefix == "/api/channels"


def test_main_app_exposes_channels_status_route():
    pytest.importorskip("fastapi")
    from api.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/channels/" in paths


def test_channels_status_without_langgraph_sdk(monkeypatch):
    pytest.importorskip("fastapi")
    import asyncio

    monkeypatch.delenv("JNAO_HARNESS_GATEWAY_URL", raising=False)
    monkeypatch.delenv("DEER_FLOW_CHANNELS_GATEWAY_URL", raising=False)

    from jnao_harness.gateway.routers.channels import get_channels_status

    result = asyncio.run(get_channels_status())
    assert result.service_running is False
    assert "feishu" in result.channels
    assert "wecom" in result.channels


def test_token_usage_route_registered():
    pytest.importorskip("fastapi")
    from api.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/threads/{thread_id}/token-usage" in paths


def test_token_usage_empty_without_harness_runtime():
    """Session summary works without DeerFlow RunStore (local SQLite)."""
    pytest.importorskip("fastapi")
    import asyncio

    from jnao_harness.gateway.routers.token_usage import thread_token_usage

    result = asyncio.run(thread_token_usage("t1"))
    assert result.thread_id == "t1"
    assert result.total_tokens == 0
    assert result.total_runs == 0
