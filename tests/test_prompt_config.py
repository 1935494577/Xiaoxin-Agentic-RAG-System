"""Prompt config API and composition."""

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"


def _load_module(name: str, rel: str):
    path = SRC / rel
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


engine = _load_module("prompt_engine_test", "agent/prompt_engine.py")
compose = engine.compose_system_prompt
default_slots = engine.default_prompt_slots
preview_layers = engine.preview_layers


@pytest.fixture
def client(tmp_path, monkeypatch):
    ui_path = tmp_path / "ui_config.json"
    prompt_path = tmp_path / "prompt_config.json"
    brand_dir = tmp_path / "branding"
    brand_dir.mkdir()
    monkeypatch.setattr("api.ui_config_store._config_path", lambda: ui_path)
    monkeypatch.setattr("api.ui_config_store._branding_dir", lambda: brand_dir)
    monkeypatch.setattr("api.prompt_config_store._config_path", lambda: prompt_path)

    from config import settings

    monkeypatch.setattr(settings, "ui_config_path", ui_path)
    monkeypatch.setattr(settings, "prompt_config_path", prompt_path)
    monkeypatch.setattr(settings, "ui_branding_dir", brand_dir)

    from api.main import app

    with TestClient(app) as c:
        yield c


def test_compose_kb_includes_persona_and_task():
    slots = default_slots()
    text = compose(slots, mode="kb", fast=False)
    assert "猫娘" in text
    assert "参考资料" in text or "知识库助手" in text


def test_compose_fast_uses_fast_task():
    slots = default_slots()
    std = compose(slots, mode="kb", fast=False)
    fast = compose(slots, mode="kb", fast=True)
    assert "可结合对话历史" in std
    assert "简洁作答" in fast
    assert "可结合对话历史" not in fast


def test_disable_persona_layer():
    slots = default_slots()
    for s in slots:
        if s["id"] == "persona":
            s["enabled"] = False
    text = compose(slots, mode="kb", fast=False)
    assert "猫娘" not in text


def test_prompt_config_api_defaults(client: TestClient):
    r = client.get("/config/prompts", params={"mode": "kb", "fast": False})
    assert r.status_code == 200
    body = r.json()
    ids = {s["id"] for s in body["slots"]}
    assert "persona" in ids
    assert "kb_task" in ids
    assert body["preview"]["composed"]


def test_prompt_config_update_persona(client: TestClient):
    r = client.get("/config/prompts")
    slots = r.json()["slots"]
    for s in slots:
        if s["id"] == "persona":
            s["content"] = "你是专业顾问，语气正式。"
    r2 = client.put("/config/prompts", json={"slots": slots})
    assert r2.status_code == 200
    assert "专业顾问" in r2.json()["preview"]["composed"]


def test_migrate_persona_from_ui_config(tmp_path, monkeypatch):
    ui_path = tmp_path / "ui_config.json"
    prompt_path = tmp_path / "prompt_config.json"
    ui_path.write_text(
        '{"chat_persona_prompt": "来自旧配置的猫娘喵"}',
        encoding="utf-8",
    )
    monkeypatch.setattr("api.ui_config_store._config_path", lambda: ui_path)
    monkeypatch.setattr("api.prompt_config_store._config_path", lambda: prompt_path)

    from api.prompt_config_store import load_prompt_config

    cfg = load_prompt_config()
    persona = next(s for s in cfg["slots"] if s["id"] == "persona")
    assert "来自旧配置的猫娘喵" in persona["content"]
