"""DF-6: channel binding code API proxies to Harness Gateway."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

ROOT_SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))


@pytest.fixture
def authed_client(tmp_path, monkeypatch):
    from app.channels import runtime_config_store as rcs
    from auth.store import create_session, init_auth_db, list_users
    from api.main import app

    store_path = tmp_path / "runtime-config.json"
    monkeypatch.setattr(rcs.ChannelRuntimeConfigStore, "__init__", lambda self, path=None: self._init_at(store_path))

    def _init_at(self, path):
        self._path = Path(path or store_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = {}
        self._lock = __import__("threading").Lock()

    monkeypatch.setattr(rcs.ChannelRuntimeConfigStore, "_init_at", _init_at, raising=False)

    init_auth_db()
    tech = next(u for u in list_users() if u["username"] == "tech1")
    token = f"channel-connect-test-{uuid.uuid4().hex}"
    create_session(user_id=tech["id"], token=token, ttl_hours=1)
    client = TestClient(app, raise_server_exceptions=True)
    return client, token


def test_connect_route_registered():
    pytest.importorskip("fastapi")
    from api.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/channels/{provider}/connect" in paths


def test_connect_returns_binding_code(authed_client, monkeypatch):
    client, token = authed_client
    monkeypatch.setenv("JNAO_HARNESS_GATEWAY_URL", "http://127.0.0.1:8011")

    async def fake_proxy(method, path, **kwargs):
        assert method == "POST"
        assert path == "/api/channels/wecom/connect"
        return {
            "provider": "wecom",
            "mode": "binding_code",
            "code": "test-bind-code",
            "instruction": "ignored",
            "expires_in": 600,
        }

    async def fake_status():
        return {"service_running": True, "channels": {"wecom": {"enabled": True, "running": True}}}

    with (
        patch("jnao_harness.gateway.routers.channel_connections.proxy_gateway_json", new=AsyncMock(side_effect=fake_proxy)),
        patch("jnao_harness.gateway.routers.channel_connections._gateway_channel_status", new=AsyncMock(side_effect=fake_status)),
        patch(
            "jnao_harness.gateway.routers.channel_connections._runtime_configured",
            return_value=True,
        ),
        patch(
            "jnao_harness.gateway.routers.channel_connections._runtime_running",
            return_value=None,
        ),
    ):
        r = client.post(
            "/api/channels/wecom/connect",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "test-bind-code"
    assert "/connect test-bind-code" in body["instruction"]
