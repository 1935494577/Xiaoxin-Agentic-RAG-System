"""API connectivity probes (health + auth-aware public config)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_API = os.environ.get("RAG_API_BASE", "http://127.0.0.1:8001")
DOCUMENTED_API_PORT = 8001
FRONTEND_PORT = 8501

HEALTH_TIMEOUT = httpx.Timeout(3.0, connect=2.0)
RETRY_COUNT = 3
RETRY_INTERVAL_SEC = 3.0

PUBLIC_CONFIG_KEYS = (
    "embedding_model",
    "reranker_model",
    "default_chat_model",
    "use_presidio_default",
)


def auth_headers_from_env() -> dict[str, str]:
    for key in ("STREAMLIT_RAG_API_SECRET", "RAG_API_SECRET"):
        v = os.environ.get(key, "").strip()
        if v:
            return {"X-API-Key": v}
    return {}


def _client(base: str, headers: dict[str, str] | None, timeout: httpx.Timeout = HEALTH_TIMEOUT) -> httpx.Client:
    h = headers or None
    return httpx.Client(base_url=base.rstrip("/"), timeout=timeout, headers=h if h else None)


def ping_health(
    api_base: str = DEFAULT_API,
    *,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout = HEALTH_TIMEOUT,
) -> tuple[bool, str]:
    base = (api_base or DEFAULT_API).rstrip("/")
    try:
        with _client(base, headers, timeout) as client:
            r = client.get("/health")
        if r.status_code == 200:
            return True, ""
        return False, f"HTTP {r.status_code}"
    except httpx.TimeoutException:
        return False, "connection timeout (API not responding; is uvicorn stuck on startup?)"
    except httpx.ConnectError:
        return False, "connection refused (API not running on this port)"
    except Exception as e:
        return False, str(e)


def ping_api_ready(
    api_base: str = DEFAULT_API,
    *,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout = HEALTH_TIMEOUT,
) -> tuple[bool, str]:
    """Health plus /config/public — catches gateway auth misconfiguration."""
    ok, msg = ping_health(api_base, headers=headers, timeout=timeout)
    if not ok:
        return False, msg

    base = (api_base or DEFAULT_API).rstrip("/")
    hdrs = headers if headers is not None else auth_headers_from_env()
    try:
        with _client(base, hdrs, timeout) as client:
            r = client.get("/config/public")
        if r.status_code == 200:
            return True, ""
        if r.status_code in (401, 403):
            return False, "unauthorized (check RAG_API_SECRET / gateway key)"
        return False, f"HTTP {r.status_code} on /config/public"
    except httpx.TimeoutException:
        return False, "connection timeout on /config/public"
    except httpx.ConnectError:
        return False, "connection refused"
    except Exception as e:
        return False, str(e)


def fetch_public_config(
    api_base: str = DEFAULT_API,
    *,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    base = (api_base or DEFAULT_API).rstrip("/")
    hdrs = headers if headers is not None else auth_headers_from_env()
    try:
        with _client(base, hdrs) as client:
            r = client.get("/config/public")
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def check_api_with_retry(
    api_base: str = DEFAULT_API,
    *,
    headers: dict[str, str] | None = None,
    retries: int = RETRY_COUNT,
    interval_sec: float = RETRY_INTERVAL_SEC,
    on_attempt: Callable[[int, int, bool, str], None] | None = None,
) -> tuple[bool, str]:
    last_msg = ""
    total = max(1, int(retries))
    for attempt in range(1, total + 1):
        ok, msg = ping_api_ready(api_base, headers=headers)
        if on_attempt:
            on_attempt(attempt, total, ok, msg)
        if ok:
            return True, ""
        last_msg = msg
        if attempt < total:
            time.sleep(interval_sec)
    return False, last_msg


def api_port_matches(url: str, expected_port: int = DOCUMENTED_API_PORT) -> bool:
    parsed = urlparse(url)
    if not parsed.port:
        return expected_port in (80, 443)
    return parsed.port == expected_port


def verify_frontend_backend_sync(
    api_base: str = DEFAULT_API,
    *,
    headers: dict[str, str] | None = None,
) -> list[str]:
    issues: list[str] = []
    if not api_port_matches(DEFAULT_API):
        issues.append(f"DEFAULT_API {DEFAULT_API!r} port != {DOCUMENTED_API_PORT}")

    ok, err = ping_api_ready(api_base, headers=headers)
    if not ok:
        issues.append(f"api ready check failed: {err}")
        return issues

    cfg = fetch_public_config(api_base, headers=headers)
    if cfg is None:
        issues.append("GET /config/public failed")
        return issues

    missing = [k for k in PUBLIC_CONFIG_KEYS if k not in cfg]
    if missing:
        issues.append(f"/config/public missing keys: {missing}")

    return issues
