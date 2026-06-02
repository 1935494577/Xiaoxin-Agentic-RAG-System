"""Model profile CRUD API."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    profiles_path = tmp_path / "model_profiles.json"
    monkeypatch.setenv("MODEL_PROFILES_PATH", str(profiles_path))
    monkeypatch.chdir(tmp_path.parent if tmp_path.parent.exists() else tmp_path)

    from config import settings

    monkeypatch.setattr(settings, "model_profiles_path", profiles_path)

    from api.main import app

    with TestClient(app) as c:
        yield c


def test_model_profile_create_get_update(client: TestClient):
    created = client.post(
        "/config/model-profiles",
        json={
            "name": "测试 DeepSeek",
            "vendor": "deepseek",
            "api_base": "https://api.deepseek.com",
            "api_path": None,
            "default_model": "deepseek-chat",
            "api_key": "sk-test-key-1234",
        },
    )
    assert created.status_code == 200
    body = created.json()
    pid = body["id"]
    assert body["name"] == "测试 DeepSeek"
    assert body["has_api_key"] is True
    assert body["api_key_hint"].endswith("1234")

    got = client.get(f"/config/model-profiles/{pid}")
    assert got.status_code == 200
    assert got.json()["default_model"] == "deepseek-chat"

    updated = client.put(
        f"/config/model-profiles/{pid}",
        json={
            "name": "DeepSeek 生产",
            "default_model": "deepseek-reasoner",
        },
    )
    assert updated.status_code == 200
    row = updated.json()
    assert row["name"] == "DeepSeek 生产"
    assert row["default_model"] == "deepseek-reasoner"
    assert row["has_api_key"] is True

    listed = client.get("/config/model-profiles")
    assert listed.status_code == 200
    profiles = listed.json()["profiles"]
    assert len(profiles) == 1
    assert profiles[0]["name"] == "DeepSeek 生产"


def test_model_profile_update_keeps_key_when_omitted(client: TestClient):
    created = client.post(
        "/config/model-profiles",
        json={
            "name": "A",
            "vendor": "custom",
            "api_base": "https://example.com",
            "default_model": "m1",
            "api_key": "secret-old",
        },
    )
    pid = created.json()["id"]

    updated = client.put(
        f"/config/model-profiles/{pid}",
        json={"name": "B"},
    )
    assert updated.status_code == 200
    assert updated.json()["has_api_key"] is True

    updated2 = client.put(
        f"/config/model-profiles/{pid}",
        json={"api_key": "secret-new"},
    )
    assert updated2.status_code == 200
    assert updated2.json()["api_key_hint"].endswith("-new")


def test_model_profile_not_found(client: TestClient):
    assert client.get("/config/model-profiles/missing").status_code == 404
    assert client.put("/config/model-profiles/missing", json={"name": "x"}).status_code == 404
