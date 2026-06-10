"""Citation / source preview API (TDD)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    try:
        from api.main import app  # noqa: PLC0415
    except ModuleNotFoundError as e:
        pytest.skip(f"API 依赖未就绪: {e}")
    with TestClient(app) as client:
        yield client


@patch("api.main.fetch_parents_by_ids")
def test_source_preview_returns_parent_text(mock_fetch, api_client):
    mock_fetch.return_value = {
        "p1": {
            "parent_id": "p1",
            "source": "docs/policy.txt",
            "department": "技术",
            "permission_label": "internal",
            "text": "每周超脑阅读一次。",
        }
    }
    r = api_client.get("/sources/preview/p1", params={"user_department": "技术"})
    assert r.status_code == 200
    body = r.json()
    assert body["parent_id"] == "p1"
    assert "每周超脑阅读" in body["text"]
    assert body["source"] == "docs/policy.txt"


@patch("api.main.fetch_parents_by_ids")
def test_source_preview_not_found(mock_fetch, api_client):
    mock_fetch.return_value = {}
    r = api_client.get("/sources/missing-id/preview", params={"user_department": "技术"})
    assert r.status_code == 404


@patch("api.main.fetch_parents_by_ids")
def test_source_preview_respects_allowed_sources(mock_fetch, api_client):
    mock_fetch.return_value {
        "p1": {
            "parent_id": "p1",
            "source": "secret/doc.txt",
            "department": "技术",
            "permission_label": "",
            "text": "机密",
        }
    }
    r = api_client.get(
        "/sources/preview/p1",
        params={"user_department": "技术", "allowed_sources": "public/doc.txt"},
    )
    assert r.status_code == 403
