"""Optional RAG_API_SECRET gate."""

import pytest
from fastapi.testclient import TestClient


def test_health_never_requires_api_key(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "rag_api_secret", "super-secret-key", raising=False)
    try:
        from api.main import app  # noqa: PLC0415

        with TestClient(app) as client:
            r = client.get("/health")
            assert r.status_code == 200
    finally:
        monkeypatch.setattr(settings, "rag_api_secret", "", raising=False)


def test_config_public_requires_key_when_secret_set(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "rag_api_secret", "only-test", raising=False)
    try:
        from api.main import app  # noqa: PLC0415

        with TestClient(app) as client:
            assert client.get("/config/public").status_code == 401
            assert client.get("/config/public", headers={"X-API-Key": "wrong"}).status_code == 401
            assert client.get("/config/public", headers={"X-API-Key": "only-test"}).status_code == 200
            assert (
                client.get("/config/public", headers={"Authorization": "Bearer only-test"}).status_code == 200
            )
    finally:
        monkeypatch.setattr(settings, "rag_api_secret", "", raising=False)
