"""Ensure admin nav registry matches Streamlit pages."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
STREAMLIT_APP = ROOT / "frontend" / "admin" / "streamlit_app.py"
CLIENT_TS = ROOT / "frontend" / "chat" / "src" / "api" / "client.ts"


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


def _parse_streamlit_pages(text: str) -> list[dict[str, str | bool]]:
    rows: list[dict[str, str | bool]] = []
    for m in re.finditer(
        r'st\.Page\("pages/([^"]+)"\s*,\s*title="([^"]+)"(?:\s*,\s*url_path="([^"]*)")?',
        text,
    ):
        module, title, url_path = m.group(1), m.group(2), m.group(3) or ""
        tail = text[m.start() : m.end() + 40]
        is_default = "default=True" in tail
        rows.append({"module": f"pages/{module}", "title": title, "url_path": url_path, "default": is_default})
    return rows


def _parse_client_nav_ids(text: str) -> list[str]:
    block = re.search(r"NAV_FALLBACK_ITEMS[^[]*\[(.*?)\];", text, re.S)
    assert block
    return re.findall(r'id:\s*"([^"]+)"', block.group(1))


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


def test_admin_pages_match_streamlit():
    nav = _load_nav_config()
    st_text = STREAMLIT_APP.read_text(encoding="utf-8")
    st_pages = _parse_streamlit_pages(st_text)
    registry = list(nav.ADMIN_PAGES)

    assert len(st_pages) == len(registry)
    for spec, page in zip(registry, st_pages, strict=True):
        assert spec["module"] == page["module"]
        assert spec["label"] == page["title"]
        assert spec.get("url_path", "") == page["url_path"]
        assert bool(spec.get("default")) == bool(page["default"])


def test_nav_api_items_match_registry():
    nav = _load_nav_config()
    cfg = nav.build_nav_config()
    admin_items = [i for i in cfg["items"] if i["id"] != "chat"]
    assert [i["id"] for i in admin_items] == [p["id"] for p in nav.ADMIN_PAGES]
    assert [i["label"] for i in admin_items] == [p["label"] for p in nav.ADMIN_PAGES]


def test_spa_nav_fallback_ids():
    nav = _load_nav_config()
    client_text = CLIENT_TS.read_text(encoding="utf-8")
    spa_ids = _parse_client_nav_ids(client_text)
    assert spa_ids == [p["id"] for p in nav.ADMIN_PAGES]


def test_nav_config_endpoint(client: TestClient):
    r = client.get("/config/nav")
    assert r.status_code == 200
    body = r.json()
    ids = [i["id"] for i in body["items"] if i["id"] != "chat"]
    nav = _load_nav_config()
    assert ids == [p["id"] for p in nav.ADMIN_PAGES]
