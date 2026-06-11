"""Agent tools config API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    cfg = tmp_path / "agent_tools.json"
    monkeypatch.setattr("config.settings.agent_tools_path", cfg)
    from api.main import app

    with TestClient(app) as c:
        yield c


def test_agent_tools_defaults(client: TestClient):
    r = client.get("/config/agent-tools")
    assert r.status_code == 200
    body = r.json()
    assert body["chat_tools_enabled"] is True
    ids = {t["id"] for t in body["tools"]}
    assert "get_weather" in ids


def test_agent_tools_update(client: TestClient):
    r = client.put(
        "/config/agent-tools",
        json={"chat_tools_enabled": True, "tools": {"get_weather": {"enabled": True}}},
    )
    assert r.status_code == 200
    assert r.json()["tools"][0]["id"] == "get_weather"
