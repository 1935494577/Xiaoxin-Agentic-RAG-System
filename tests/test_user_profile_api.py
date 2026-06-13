"""User profile API — SQLite persistence."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "profiles.db"
    monkeypatch.setattr("config.settings.chat_sessions_db_path", db)
    from api.chat_session_store import init_chat_session_db
    from api.user_profile_store import init_user_profile_db

    init_chat_session_db()
    init_user_profile_db()
    from api.main import app

    return TestClient(app)


def test_get_profile_creates_default(client):
    r = client.get("/users/profile", params={"user_id": "u_test_1"})
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "u_test_1"
    assert body["department"] == "技术部"
    assert body["display_name"] == ""
    assert body["avatar_url"] == ""


def test_update_profile(client):
    r = client.put(
        "/users/profile",
        json={
            "user_id": "u_test_2",
            "display_name": "风停看雨画",
            "department": "运营部",
            "avatar_url": "data:image/png;base64,abc",
            "ai_display_name": "小脑",
            "ai_avatar_url": "data:image/png;base64,xyz",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "风停看雨画"
    assert body["department"] == "运营部"
    assert body["avatar_url"].startswith("data:image/")
    assert body["ai_display_name"] == "小脑"
    assert body["ai_avatar_url"].startswith("data:image/")

    r2 = client.get("/users/profile", params={"user_id": "u_test_2"})
    assert r2.json()["display_name"] == "风停看雨画"


def test_reject_invalid_department(client):
    r = client.put(
        "/users/profile",
        json={"user_id": "u_x", "department": "不存在部门"},
    )
    assert r.status_code == 400


def test_reject_oversized_avatar(client):
    r = client.put(
        "/users/profile",
        json={"user_id": "u_x", "avatar_url": "data:image/png;base64," + ("x" * 600_001)},
    )
    assert r.status_code in (400, 422)
