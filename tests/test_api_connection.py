"""API 连通性与重试逻辑测试（不依赖 Streamlit UI）。"""

from __future__ import annotations

import httpx
import pytest

from connection_helpers import (
    DEFAULT_API,
    DOCUMENTED_API_PORT,
    FRONTEND_PORT,
    PUBLIC_CONFIG_KEYS,
    RETRY_COUNT,
    RETRY_INTERVAL_SEC,
    check_api_with_retry,
    fetch_public_config,
    ping_health,
    verify_frontend_backend_sync,
)


def test_retry_policy_constants():
    assert RETRY_COUNT == 3
    assert RETRY_INTERVAL_SEC == 3.0


def test_default_api_uses_documented_port():
    assert str(DOCUMENTED_API_PORT) in DEFAULT_API


def test_frontend_port_constant():
    assert FRONTEND_PORT == 8501


def test_ping_health_success(monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return {"status": "ok"}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def get(self, path):
            assert path == "/health"
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    ok, msg = ping_health("http://127.0.0.1:8001")
    assert ok is True
    assert msg == ""


def test_ping_health_connect_error(monkeypatch):
    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def get(self, path):
            raise httpx.ConnectError("refused", request=httpx.Request("GET", "http://x/health"))

    monkeypatch.setattr(httpx, "Client", FakeClient)
    ok, msg = ping_health("http://127.0.0.1:8001")
    assert ok is False
    assert "connection refused" in msg


def test_check_api_with_retry_succeeds_on_third_attempt(monkeypatch):
    health_attempts = {"n": 0}

    class FakeResp:
        status_code = 200

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def get(self, path):
            if path == "/health":
                health_attempts["n"] += 1
                if health_attempts["n"] < 3:
                    raise httpx.ConnectError("refused", request=httpx.Request("GET", "http://x/health"))
                return FakeResp()
            if path == "/config/public":
                return FakeResp()
            raise AssertionError(path)

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr("api.connectivity.time.sleep", lambda _s: None)

    attempts: list[tuple[int, int, bool, str]] = []

    def on_attempt(attempt, total, ok, msg):
        attempts.append((attempt, total, ok, msg))

    ok, msg = check_api_with_retry(retries=3, interval_sec=3, on_attempt=on_attempt)
    assert ok is True
    assert msg == ""
    assert health_attempts["n"] == 3
    assert len(attempts) == 3


def test_ping_api_ready_rejects_unauthorized(monkeypatch):
    class FakeResp:
        status_code = 401

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def get(self, path):
            if path == "/health":
                return type("R", (), {"status_code": 200})()
            if path == "/config/public":
                return FakeResp()
            raise AssertionError(path)

    monkeypatch.setattr(httpx, "Client", FakeClient)
    from api.connectivity import ping_api_ready

    ok, msg = ping_api_ready("http://127.0.0.1:8001")
    assert ok is False
    assert "unauthorized" in msg


def test_public_config_schema_via_testclient():
    try:
        from api.main import app  # noqa: PLC0415
    except ModuleNotFoundError as e:
        pytest.skip(f"API deps not ready: {e}")

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        r = client.get("/config/public")
        assert r.status_code == 200
        body = r.json()
        for key in PUBLIC_CONFIG_KEYS:
            assert key in body


def test_health_via_testclient():
    try:
        from api.main import app  # noqa: PLC0415
    except ModuleNotFoundError as e:
        pytest.skip(f"API deps not ready: {e}")

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.integration
def test_live_api_connection_if_running():
    """仅当本地 API 已启动时执行；未启动则 skip。"""
    ok, _ = ping_health()
    if not ok:
        pytest.skip("Local API not running on DEFAULT_API")
    issues = verify_frontend_backend_sync()
    assert issues == []
