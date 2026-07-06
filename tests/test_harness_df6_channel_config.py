"""DF-6: DeerFlow-style channel provider config API (runtime credentials)."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

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
    token = f"channel-config-test-{uuid.uuid4().hex}"
    create_session(user_id=tech["id"], token=token, ttl_hours=1)
    client = TestClient(app, raise_server_exceptions=True)
    return client, token, tech


def test_channel_providers_route_registered():
    pytest.importorskip("fastapi")
    from api.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/channels/providers" in paths


def test_channel_providers_list(authed_client):
    client, token, _tech = authed_client
    r = client.get("/api/channels/providers", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    names = {p["provider"] for p in body["providers"]}
    assert "feishu" in names
    assert "wecom" in names


def test_channel_runtime_config_save(authed_client):
    client, token, _tech = authed_client
    r = client.post(
        "/api/channels/feishu/runtime-config",
        headers={"Authorization": f"Bearer {token}"},
        json={"values": {"app_id": "cli_test", "app_secret": "sec_test"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "feishu"
    assert body["configured"] is True
    assert body["credential_values"]["app_id"] == "cli_test"
    assert body["credential_values"]["app_secret"] == "********"
