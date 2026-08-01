"""Regression: exam bank tenant scope must come from authenticated actor only."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def exam_client(tmp_path, monkeypatch):
    from auth import middleware
    from auth.middleware import SessionAuthMiddleware
    from exam_bank import store
    from tenant.context import TenantContextMiddleware

    db = tmp_path / "exam_bank.db"
    monkeypatch.setattr(store.settings, "exam_bank_db_path", db)
    store.init_exam_bank_db()

    users = {
        "internal-token": {
            "id": "u-internal",
            "username": "internal-user",
            "tenant_id": "internal",
            "department": "general",
        },
        "acme-token": {
            "id": "u-acme",
            "username": "acme-user",
            "tenant_id": "acme",
            "department": "general",
        },
        "alice-token": {
            "id": "alice",
            "username": "alice",
            "tenant_id": "internal",
            "department": "general",
        },
        "bob-token": {
            "id": "bob",
            "username": "bob",
            "tenant_id": "internal",
            "department": "general",
        },
    }
    monkeypatch.setattr(middleware, "resolve_session", lambda token: users.get(token))

    from api.exam_router import router as exam_router

    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(SessionAuthMiddleware)
    app.include_router(exam_router)

    with TestClient(app) as client:
        yield client, store


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_collection_ignores_body_tenant_id(exam_client):
    client, _store = exam_client
    response = client.post(
        "/api/exam/collections",
        json={
            "name": "ignored",
            "subject": "数学",
            "grade": "高一",
            "region": "杭州",
            "tenant_id": "acme",
        },
        headers=_headers("internal-token"),
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "internal"


def test_list_collections_ignores_query_tenant_id(exam_client):
    client, store = exam_client
    store.create_collection(
        name="internal库",
        subject="数学",
        grade="高二",
        region="宁波",
        tenant_id="internal",
        visibility="tenant_shared",
    )
    store.create_collection(
        name="acme库",
        subject="数学",
        grade="高二",
        region="温州",
        tenant_id="acme",
        visibility="tenant_shared",
    )

    as_internal = client.get(
        "/api/exam/collections?tenant_id=acme",
        headers=_headers("internal-token"),
    )
    assert as_internal.status_code == 200
    regions = {row["region"] for row in as_internal.json()["items"]}
    assert "宁波" in regions
    assert "温州" not in regions

    as_acme = client.get("/api/exam/collections", headers=_headers("acme-token"))
    assert as_acme.status_code == 200
    regions_acme = {row["region"] for row in as_acme.json()["items"]}
    assert "温州" in regions_acme
    assert "宁波" not in regions_acme


def test_cross_tenant_collection_access_returns_not_found(exam_client):
    client, store = exam_client
    col = store.create_collection(
        name="私有库",
        subject="数学",
        grade="高三",
        region="杭州",
        tenant_id="internal",
        visibility="private",
        owner_user_id="u-internal",
    )

    denied = client.get(
        f"/api/exam/collections/{col['id']}",
        headers=_headers("acme-token"),
    )
    assert denied.status_code == 404

    allowed = client.get(
        f"/api/exam/collections/{col['id']}",
        headers=_headers("internal-token"),
    )
    assert allowed.status_code == 200
    assert allowed.json()["id"] == col["id"]


def test_ingest_commit_uses_authenticated_tenant(exam_client):
    client, store = exam_client
    col = store.create_collection(
        name="入库库",
        subject="数学",
        grade="高一",
        region="杭州",
        tenant_id="internal",
        visibility="tenant_shared",
    )
    response = client.post(
        "/api/exam/ingest/commit",
        json={
            "collection_id": col["id"],
            "title": "测试卷",
            "tenant_id": "acme",
            "items": [
                {
                    "question_no": "1",
                    "qtype": "choice",
                    "stem": "1+1=?",
                    "options": ["1", "2"],
                    "answer": "B",
                    "analysis": "",
                    "selected": True,
                }
            ],
        },
        headers=_headers("internal-token"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["questions"][0]["tenant_id"] == "internal"
    assert body["source_paper"]["tenant_id"] == "internal"


def test_create_collection_binds_owner_from_auth(exam_client):
    client, _store = exam_client
    response = client.post(
        "/api/exam/collections",
        json={
            "name": "owner-test",
            "subject": "数学",
            "grade": "高一",
            "region": "杭州",
            "owner_user_id": "attacker",
        },
        headers=_headers("alice-token"),
    )
    assert response.status_code == 200
    assert response.json()["owner_user_id"] == "alice"


def test_list_collections_ignores_query_reader_user_id(exam_client):
    client, store = exam_client
    store.create_collection(
        name="alice私有",
        subject="数学",
        grade="高二",
        region="绍兴",
        tenant_id="internal",
        visibility="private",
        owner_user_id="alice",
    )
    store.create_collection(
        name="共享库",
        subject="数学",
        grade="高二",
        region="湖州",
        tenant_id="internal",
        visibility="tenant_shared",
    )

    as_bob = client.get(
        "/api/exam/collections?reader_user_id=alice",
        headers=_headers("bob-token"),
    )
    assert as_bob.status_code == 200
    regions = {row["region"] for row in as_bob.json()["items"]}
    assert "绍兴" not in regions
    assert "湖州" in regions


def test_chat_attempt_binds_user_from_auth(exam_client):
    client, store = exam_client
    col = store.create_collection(
        name="答题库",
        subject="数学",
        grade="高一",
        region="嘉兴",
        tenant_id="internal",
        visibility="tenant_shared",
        owner_user_id="alice",
    )
    q = store.create_question(
        collection_id=col["id"],
        qtype="choice",
        stem="2+2=?",
        options=["3", "4"],
        answer="B",
    )
    sp = store.create_source_paper(
        collection_id=col["id"],
        title="单元测",
        source_filename="t.docx",
        raw_text="",
        question_ids=[q["id"]],
        tenant_id="internal",
    )

    started = client.post(
        "/api/exam/chat/attempts",
        json={"source_paper_id": sp["id"], "user_id": "alice"},
        headers=_headers("bob-token"),
    )
    assert started.status_code == 200
    attempt_id = started.json()["attempt_id"]
    row = store.get_exam_attempt(attempt_id)
    assert row is not None
    assert row["user_id"] == "bob"
