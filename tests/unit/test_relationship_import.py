"""Tests for structured relationship ingest API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def graph_db(tmp_path, monkeypatch):
    db = tmp_path / "import_graph.db"
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    yield db
    monkeypatch.setattr("graph.store._conn", None)


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def test_ingest_relationships_endpoint(client, graph_db):
    payload = {
        "source": "api_org_chart",
        "department": "技术部",
        "people": [
            {"name": "孙八", "title": "架构师", "bio": "系统架构"},
            {"name": "周九", "title": "CTO"},
        ],
        "relationships": [
            {"from_name": "孙八", "relation": "汇报", "to_name": "周九"},
        ],
    }
    r = client.post("/ingest/relationships", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["people_imported"] == 2
    assert data["relationships_imported"] == 1
    assert data["source"] == "api_org_chart"

    from graph.viz import build_graph_viz

    viz = build_graph_viz(center="孙八", department="技术部")
    assert len(viz["edges"]) >= 1
