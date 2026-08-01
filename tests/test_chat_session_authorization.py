"""Regression coverage for authenticated chat-session ownership."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.chat_session_store import create_session, init_chat_session_db
from api.schemas import ChatRequest
from config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "chat_sessions_db_path", tmp_path / "chat_sessions.db")
    monkeypatch.setattr(settings, "ephemeral_docs_dir", tmp_path / "ephemeral")
    monkeypatch.setattr(settings, "rag_api_secret", "")
    monkeypatch.setattr(settings, "rag_admin_api_secret", "")
    init_chat_session_db()

    from auth import middleware
    from api.main import app

    users = {
        "owner-token": {"id": "owner", "username": "owner", "department": "general"},
        "attacker-token": {"id": "attacker", "username": "attacker", "department": "general"},
    }
    monkeypatch.setattr(middleware, "resolve_session", lambda token: users.get(token))
    return TestClient(app)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_chat_sessions_ignore_client_supplied_user_id(client):
    owner_session = create_session("owner", title="owner chat")

    owner_list = client.get("/chat/sessions", headers={**_headers("owner-token"), "X-Tenant-ID": "acme"})
    assert owner_list.status_code == 200
    assert [row["id"] for row in owner_list.json()] == [owner_session["id"]]

    listed = client.get("/chat/sessions?user_id=owner", headers=_headers("attacker-token"))
    assert listed.status_code == 200
    assert listed.json() == []

    created = client.post(
        "/chat/sessions",
        json={"user_id": "owner", "title": "attacker chat"},
        headers=_headers("attacker-token"),
    )
    assert created.status_code == 200
    assert created.json()["user_id"] == "attacker"

    messages = client.get(
        f"/chat/sessions/{owner_session['id']}/messages?user_id=owner",
        headers=_headers("attacker-token"),
    )
    assert messages.status_code == 404

    appended = client.post(
        f"/chat/sessions/{owner_session['id']}/messages",
        json={"user_id": "owner", "messages": [{"role": "user", "content": "steal"}]},
        headers=_headers("attacker-token"),
    )
    assert appended.status_code == 404

    deleted = client.delete(
        f"/chat/sessions/{owner_session['id']}?user_id=owner",
        headers=_headers("attacker-token"),
    )
    assert deleted.status_code == 404


def test_document_upload_requires_session_owner(client):
    owner_session = create_session("owner", title="owner chat")
    response = client.post(
        f"/chat/documents/upload?session_id={owner_session['id']}&user_id=owner",
        files={"file": ("notes.txt", b"private notes", "text/plain")},
        headers=_headers("attacker-token"),
    )
    assert response.status_code == 404


def test_chat_request_identity_is_bound_to_authenticated_actor(client):
    from api.main import _authenticated_chat_request

    request = Request({"type": "http", "method": "POST", "path": "/chat", "headers": []})
    request.state.auth_user = {"id": "attacker", "department": "general"}
    bound = _authenticated_chat_request(
        ChatRequest(message="hello", user_id="owner", user_department="owner-department"),
        request,
    )

    assert bound.user_id == "attacker"
    assert bound.user_department == "general"
