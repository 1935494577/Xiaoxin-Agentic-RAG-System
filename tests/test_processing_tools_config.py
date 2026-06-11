"""Processing tools config API — use_llm_router field alignment."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    cfg = tmp_path / "processing_tools.json"
    monkeypatch.setattr("config.settings.processing_tools_path", cfg)
    from api.main import app

    with TestClient(app) as c:
        yield c


def test_processing_tools_defaults(client: TestClient):
    r = client.get("/config/processing-tools")
    assert r.status_code == 200
    body = r.json()
    assert "use_llm_router" in body
    assert isinstance(body["use_llm_router"], bool)
    assert body["tools"]


def test_processing_tools_update_use_llm_router(client: TestClient):
    r = client.put(
        "/config/processing-tools",
        json={"use_llm_router": False, "tools": {"extract_pdf": {"enabled": False}}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["use_llm_router"] is False
    pdf = next(t for t in body["tools"] if t["id"] == "extract_pdf")
    assert pdf["enabled"] is False

    r2 = client.get("/config/processing-tools")
    assert r2.json()["use_llm_router"] is False
