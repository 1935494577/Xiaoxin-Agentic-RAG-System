"""Department-based admin feature access (employee portal)."""

import pytest
from urllib.parse import quote

from fastapi import FastAPI
from fastapi.testclient import TestClient

from security.department_features import (
    FULL_ACCESS_DEPARTMENT,
    can_access_feature,
    feature_for_request,
    normalize_department,
    should_enforce_department,
)

OPS_DEPT = quote("运营部", safe="")


def test_tech_department_has_full_access():
    assert can_access_feature(FULL_ACCESS_DEPARTMENT, "vector_store") is True
    assert can_access_feature(FULL_ACCESS_DEPARTMENT, "feedback") is True


def test_non_tech_limited_features():
    for dept in ("运营部", "媒体部", "剪辑部"):
        assert can_access_feature(dept, "ingest") is True
        assert can_access_feature(dept, "prompts") is True
        assert can_access_feature(dept, "models") is True
        assert can_access_feature(dept, "scenarios") is True
        assert can_access_feature(dept, "tutorial") is True
        assert can_access_feature(dept, "processing") is False
        assert can_access_feature(dept, "memory") is False


def test_missing_department_does_not_restrict():
    assert should_enforce_department(None) is False
    assert should_enforce_department("") is False
    assert can_access_feature(None, "feedback") is True


def test_normalize_department_decodes_url_encoded_header():
    assert normalize_department(OPS_DEPT) == "运营部"


def test_feature_for_request_paths():
    assert feature_for_request("GET", "/config/prompts") == "prompts"
    assert feature_for_request("POST", "/ingest/text") == "ingest"
    assert feature_for_request("PUT", "/config/ui") == "memory"
    assert feature_for_request("GET", "/config/ui") is None
    assert feature_for_request("GET", "/health") is None


@pytest.fixture
def dept_client():
    from api.department_auth import DepartmentFeatureMiddleware

    app = FastAPI()
    app.add_middleware(DepartmentFeatureMiddleware)

    @app.get("/config/prompts")
    def prompts():
        return {"ok": True}

    @app.put("/config/prompts")
    def update_prompts():
        return {"ok": True}

    @app.get("/config/processing-tools")
    def processing():
        return {"ok": True}

    @app.get("/config/ui")
    def ui():
        return {"ok": True}

    with TestClient(app) as client:
        yield client


def test_middleware_allows_prompts_for_ops(dept_client):
    r = dept_client.get("/config/prompts", headers={"X-User-Department": OPS_DEPT})
    assert r.status_code == 200


def test_middleware_blocks_processing_for_ops(dept_client):
    r = dept_client.get(
        "/config/processing-tools",
        headers={"X-User-Department": OPS_DEPT},
    )
    assert r.status_code == 403


def test_middleware_allows_ui_get_for_ops(dept_client):
    r = dept_client.get("/config/ui", headers={"X-User-Department": OPS_DEPT})
    assert r.status_code == 200


def test_middleware_allows_all_without_department_header(dept_client):
    r = dept_client.get("/config/processing-tools")
    assert r.status_code == 200
