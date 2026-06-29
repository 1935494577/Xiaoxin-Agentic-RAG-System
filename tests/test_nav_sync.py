"""Ensure backend nav registry matches React SPA sidebar (departmentAccess.ts)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
DEPT_ACCESS_TS = ROOT / "frontend" / "src" / "lib" / "departmentAccess.ts"


def _load_nav_config():
    import importlib.util
    import sys

    path = SRC / "api" / "nav_config.py"
    spec = importlib.util.spec_from_file_location("nav_config_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nav_config_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _parse_spa_nav_ids(text: str) -> list[str]:
    block = re.search(r"export const ALL_NAV_ITEMS.*?=\s*\[(.*?)\];", text, re.S)
    assert block, "ALL_NAV_ITEMS not found in departmentAccess.ts"
    return re.findall(r'id:\s*"([^"]+)"', block.group(1))


def _parse_spa_nav_labels(text: str) -> dict[str, str]:
    block = re.search(r"export const ALL_NAV_ITEMS.*?=\s*\[(.*?)\];", text, re.S)
    assert block, "ALL_NAV_ITEMS not found in departmentAccess.ts"
    pairs = re.findall(r'id:\s*"([^"]+)".*?label:\s*"([^"]+)"', block.group(1), re.S)
    return dict(pairs)


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


def test_spa_nav_ids_match_registry():
    nav = _load_nav_config()
    spa_text = DEPT_ACCESS_TS.read_text(encoding="utf-8")
    spa_ids = [i for i in _parse_spa_nav_ids(spa_text) if i != "chat"]
    assert spa_ids == [p["id"] for p in nav.ADMIN_PAGES]


def test_spa_nav_labels_match_registry():
    nav = _load_nav_config()
    spa_text = DEPT_ACCESS_TS.read_text(encoding="utf-8")
    labels = _parse_spa_nav_labels(spa_text)
    for page in nav.ADMIN_PAGES:
        assert labels.get(page["id"]) == page["label"], page["id"]


def test_nav_api_items_match_registry():
    nav = _load_nav_config()
    cfg = nav.build_nav_config()
    admin_items = [i for i in cfg["items"] if i["id"] != "chat"]
    assert [i["id"] for i in admin_items] == [p["id"] for p in nav.ADMIN_PAGES]
    assert [i["label"] for i in admin_items] == [p["label"] for p in nav.ADMIN_PAGES]
    assert cfg["admin_url"].endswith("/admin")


def test_nav_config_endpoint(client: TestClient):
    r = client.get("/config/nav")
    assert r.status_code == 200
    body = r.json()
    ids = [i["id"] for i in body["items"] if i["id"] != "chat"]
    nav = _load_nav_config()
    assert ids == [p["id"] for p in nav.ADMIN_PAGES]
