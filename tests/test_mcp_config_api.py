"""MCP configuration API (Main API 8010 admin)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    ext_cfg = tmp_path / "extensions_config.json"
    ext_cfg.write_text(json.dumps({"mcpServers": {}, "skills": {}}), encoding="utf-8")
    monkeypatch.setenv("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(ext_cfg))
    monkeypatch.setenv("DEER_FLOW_PROJECT_ROOT", str(REPO_ROOT))

    async def _noop_admin(_request, detail=""):
        return None

    monkeypatch.setattr(
        "jnao_harness.gateway.routers.mcp.require_admin_user",
        _noop_admin,
    )

    from jnao_harness.gateway.routers.mcp import router as mcp_router

    app = FastAPI()
    app.include_router(mcp_router)

    with TestClient(app) as c:
        yield c, ext_cfg


def test_mcp_router_imports_without_deerflow(monkeypatch):
    """Main API .venv may lack deerflow; router must still import."""
    monkeypatch.delenv("DEER_FLOW_EXTENSIONS_CONFIG_PATH", raising=False)
    from jnao_harness.gateway.routers import mcp as mcp_module

    assert mcp_module.router is not None


def test_mcp_config_get_empty(client, monkeypatch):
    c, _ = client
    monkeypatch.delenv("REEFAPI_KEY", raising=False)
    monkeypatch.setattr("config.settings.reefapi_key", "", raising=False)
    r = c.get("/api/mcp/config")
    assert r.status_code == 200
    body = r.json()
    assert body["mcp_servers"] == {}
    assert "config_path" in body


def test_mcp_config_get_reefapi_tools(client, monkeypatch):
    c, ext_cfg = client
    body = {
        "mcp_servers": {
            "reefapi": {
                "enabled": True,
                "type": "http",
                "command": None,
                "args": [],
                "env": {},
                "url": "https://api.reefapi.com/mcp",
                "headers": {"Authorization": "Bearer test-key"},
                "description": "ReefAPI",
            }
        }
    }
    with patch(
        "jnao_harness.gateway.routers.mcp.reset_local_mcp_cache_if_available",
    ), patch(
        "jnao_harness.gateway.routers.mcp._reset_gateway_mcp_cache",
        new=AsyncMock(),
    ):
        c.put("/api/mcp/config", json=body)
    r = c.get("/api/mcp/config")
    assert r.status_code == 200
    body = r.json()
    assert "reefapi" in body["mcp_servers"]
    entry = body["mcp_servers"]["reefapi"]
    assert entry["suggested"] is False
    assert entry["config"]["type"] == "http"
    tools = entry["tools"]
    assert len(tools) == 5
    names = {t["name"] for t in tools}
    assert names == {
        "search_engines",
        "get_catalog",
        "get_engine_schema",
        "get_action_schema",
        "call_engine",
    }
    call_engine = next(t for t in tools if t["name"] == "call_engine")
    assert call_engine["requires_key"] is True


def test_mcp_config_put_http_server(client):
    c, ext_cfg = client
    body = {
        "mcp_servers": {
            "reefapi": {
                "enabled": True,
                "type": "http",
                "command": None,
                "args": [],
                "env": {},
                "url": "https://api.reefapi.com/mcp",
                "headers": {"Authorization": "Bearer test-key"},
                "description": "ReefAPI",
            }
        }
    }
    with patch(
        "jnao_harness.gateway.routers.mcp.reset_local_mcp_cache_if_available",
    ), patch(
        "jnao_harness.gateway.routers.mcp._reset_gateway_mcp_cache",
        new=AsyncMock(),
    ):
        r = c.put("/api/mcp/config", json=body)
    assert r.status_code == 200
    resp = r.json()
    assert "reefapi" in resp["mcp_servers"]
    entry = resp["mcp_servers"]["reefapi"]
    assert entry["config"]["headers"]["Authorization"] == "***"
    assert entry["suggested"] is False
    assert len(entry["tools"]) == 5

    saved = json.loads(ext_cfg.read_text(encoding="utf-8"))
    assert saved["mcpServers"]["reefapi"]["url"] == "https://api.reefapi.com/mcp"
    assert saved["mcpServers"]["reefapi"]["headers"]["Authorization"] == "Bearer test-key"


def test_mcp_config_stdio_requires_allowed_command(client):
    c, _ = client
    body = {
        "mcp_servers": {
            "bad": {
                "enabled": True,
                "type": "stdio",
                "command": "python",
                "args": ["server.py"],
                "env": {},
                "url": None,
                "headers": {},
                "description": "",
            }
        }
    }
    r = c.put("/api/mcp/config", json=body)
    assert r.status_code == 400
    assert "python" in r.json()["detail"]


def test_mcp_config_mask_roundtrip(client):
    c, ext_cfg = client
    initial = {
        "mcp_servers": {
            "demo": {
                "enabled": True,
                "type": "http",
                "url": "https://example.com/mcp",
                "headers": {"X-Token": "secret-1"},
                "env": {},
                "args": [],
                "description": "",
            }
        }
    }
    with patch("jnao_harness.gateway.routers.mcp.reset_local_mcp_cache_if_available"), patch(
        "jnao_harness.gateway.routers.mcp._reset_gateway_mcp_cache",
        new=AsyncMock(),
    ):
        c.put("/api/mcp/config", json=initial)
        masked = c.get("/api/mcp/config").json()
        toggle = {
            "mcp_servers": {
                "demo": {
                    **masked["mcp_servers"]["demo"]["config"],
                    "enabled": False,
                }
            }
        }
        r = c.put("/api/mcp/config", json=toggle)
    assert r.status_code == 200
    saved = json.loads(ext_cfg.read_text(encoding="utf-8"))
    assert saved["mcpServers"]["demo"]["headers"]["X-Token"] == "secret-1"
    assert saved["mcpServers"]["demo"]["enabled"] is False


def test_mcp_cache_reset(client):
    c, _ = client
    with patch(
        "jnao_harness.gateway.routers.mcp.reset_local_mcp_cache_if_available"
    ) as reset_local, patch(
        "jnao_harness.gateway.routers.mcp._reset_gateway_mcp_cache",
        new=AsyncMock(),
    ) as reset_gw:
        r = c.post("/api/mcp/cache/reset")
    assert r.status_code == 200
    assert r.json()["success"] is True
    reset_local.assert_called_once()
    reset_gw.assert_awaited_once()
