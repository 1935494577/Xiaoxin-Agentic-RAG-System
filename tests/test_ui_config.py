"""UI branding config API."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    ui_path = tmp_path / "ui_config.json"
    brand_dir = tmp_path / "branding"
    brand_dir.mkdir()
    monkeypatch.setattr("api.ui_config_store._config_path", lambda: ui_path)
    monkeypatch.setattr("api.ui_config_store._branding_dir", lambda: brand_dir)

    from config import settings

    monkeypatch.setattr(settings, "ui_config_path", ui_path)
    monkeypatch.setattr(settings, "ui_branding_dir", brand_dir)

    from api.main import app

    with TestClient(app) as c:
        yield c


def test_ui_config_defaults(client: TestClient):
    r = client.get("/config/ui")
    assert r.status_code == 200
    body = r.json()
    assert body["logo_en"] == "JNAO"
    assert body["logo_cn"] == "劲脑"
    assert body["agent_reasoning_mode"] == "direct"
    assert body["scene_preset"] == "kb_frontline"
    assert len(body.get("scene_presets") or []) >= 3
    assert "txt" in body["supported_upload_extensions"]


def test_apply_scene_preset(client: TestClient):
    r = client.post("/config/ui/scene-preset/internal_full")
    assert r.status_code == 200
    body = r.json()
    assert body["scene_preset"] == "internal_full"
    assert body["hybrid_expert_mode"] is True
    assert body["agent_reasoning_mode"] == "react"

    r2 = client.post("/config/ui/scene-preset/kb_frontline")
    assert r2.status_code == 200
    assert r2.json()["hybrid_expert_mode"] is False
    assert r2.json()["agent_reasoning_mode"] == "direct"


def test_apply_unknown_scene_preset_400(client: TestClient):
    r = client.post("/config/ui/scene-preset/not-a-preset")
    assert r.status_code == 400


def test_ui_config_update(client: TestClient):
    r = client.put(
        "/config/ui",
        json={
            "logo_en": "ACME",
            "logo_cn": "测试",
            "app_title": "测试助手",
            "suggested_questions": ["问题一", "问题二"],
            "ingest_tag_presets": ["制度", "培训"],
        },
    )
    assert r.status_code == 200
    assert r.json()["logo_en"] == "ACME"
    assert len(r.json()["suggested_questions"]) == 2
    assert r.json()["ingest_tag_presets"] == ["制度", "培训"]

    r2 = client.get("/config/ui")
    assert r2.json()["app_title"] == "测试助手"
