"""TenantContext middleware (Sprint E1)."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tenant.context import TenantContextMiddleware, get_tenant_id


@pytest.fixture()
def tenant_app():
    app = FastAPI()
    app.add_middleware(TenantContextMiddleware)

    @app.get("/echo-tenant")
    def echo_tenant(request: Request):
        return {"tenant_id": get_tenant_id(request)}

    return app


def test_default_tenant_is_internal(tenant_app):
    with TestClient(tenant_app) as client:
        r = client.get("/echo-tenant")
        assert r.status_code == 200
        assert r.json()["tenant_id"] == "internal"


def test_tenant_from_header(tenant_app):
    with TestClient(tenant_app) as client:
        r = client.get("/echo-tenant", headers={"X-Tenant-ID": "acme-corp"})
        assert r.status_code == 200
        assert r.json()["tenant_id"] == "acme-corp"


def test_empty_tenant_header_falls_back_internal(tenant_app):
    with TestClient(tenant_app) as client:
        r = client.get("/echo-tenant", headers={"X-Tenant-ID": "  "})
        assert r.json()["tenant_id"] == "internal"
