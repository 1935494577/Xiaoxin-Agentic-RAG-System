"""Auth system tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth.password import hash_password, verify_password
from auth.service import login, seed_default_users_if_empty
from auth.store import init_auth_db


def test_password_hash_roundtrip():
    h, s = hash_password("secret123")
    assert verify_password("secret123", h, s)
    assert not verify_password("wrong", h, s)


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    db = tmp_path / "auth.db"
    monkeypatch.setattr("auth.store.settings.auth_db_path", db)
    monkeypatch.setattr("config.settings.auth_db_path", db)
    cred = tmp_path / "creds.txt"
    monkeypatch.setattr("auth.service.settings.auth_bootstrap_credentials_path", cred)
    monkeypatch.setattr("config.settings.auth_bootstrap_credentials_path", cred)

    from auth.middleware import SessionAuthMiddleware
    from auth.router import router as auth_router

    init_auth_db()
    seed_default_users_if_empty()

    app = FastAPI()
    app.add_middleware(SessionAuthMiddleware)
    app.include_router(auth_router)

    @app.get("/protected")
    def protected():
        return {"ok": True}

    with TestClient(app) as client:
        yield client


def test_login_and_me(auth_client):
    r = auth_client.post("/auth/login", json={"username": "tech1", "password": "x"})
    assert r.status_code == 401

    cred_path = auth_client.app  # noqa - get password from seed file
    from config import settings

    text = settings.auth_bootstrap_credentials_path.read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("技术部") and "tech1" in l)
    password = line.split("\t")[2]

    r = auth_client.post("/auth/login", json={"username": "tech1", "password": password, "remember": True})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    assert r.json()["user"]["department"] == "技术部"

    r2 = auth_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["username"] == "tech1"

    r3 = auth_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200

    r4 = auth_client.get("/protected")
    assert r4.status_code == 401


def test_change_password(auth_client):
    from config import settings

    text = settings.auth_bootstrap_credentials_path.read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if "ops1" in l)
    password = line.split("\t")[2]
    r = auth_client.post("/auth/login", json={"username": "ops1", "password": password})
    token = r.json()["token"]

    bad = auth_client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "wrong", "new_password": "newpass99"},
    )
    assert bad.status_code == 401

    ok = auth_client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": password, "new_password": "newpass99"},
    )
    assert ok.status_code == 200

    relog = auth_client.post("/auth/login", json={"username": "ops1", "password": "newpass99"})
    assert relog.status_code == 200


def test_tech_admin_list_users(auth_client):
    from config import settings

    text = settings.auth_bootstrap_credentials_path.read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if "tech1" in l)
    password = line.split("\t")[2]
    r = auth_client.post("/auth/login", json={"username": "tech1", "password": password})
    token = r.json()["token"]

    users = auth_client.get("/auth/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200
    assert len(users.json()["users"]) == 6

    ops_line = next(l for l in text.splitlines() if "ops1" in l)
    ops_pw = ops_line.split("\t")[2]
    ops = auth_client.post("/auth/login", json={"username": "ops1", "password": ops_pw})
    ops_token = ops.json()["token"]
    denied = auth_client.get("/auth/admin/users", headers={"Authorization": f"Bearer {ops_token}"})
    assert denied.status_code == 403
