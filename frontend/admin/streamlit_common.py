"""Shared HTTP helpers for Streamlit pages (no connection-test UI logic)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx

DEFAULT_API = os.environ.get("RAG_API_BASE", "http://127.0.0.1:8010")
INGEST_TIMEOUT = 300.0
HEALTH_TIMEOUT = httpx.Timeout(3.0, connect=2.0)

SERVICE_UNAVAILABLE = "服务暂时不可用，请稍后再试。"
AUTH_REQUIRED = "访问被拒绝，请检查网关密钥配置。"


def _api_src_on_path() -> None:
    root = Path(__file__).resolve().parents[2]
    src = str(root / "enterprise_rag" / "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def _env_api_base() -> str:
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("RAG_API_BASE="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    return os.environ.get("RAG_API_BASE", "").strip() or DEFAULT_API


def sync_api_base_session() -> str:
    """Prefer .env RAG_API_BASE so port changes (e.g. 8001→8010) take effect."""
    target = _env_api_base()
    try:
        import streamlit as st

        cur = (st.session_state.get("rag_api_base") or "").strip()
        if not cur or cur.rstrip("/") != target.rstrip("/"):
            st.session_state.rag_api_base = target
    except Exception:
        pass
    return target


def get_api_base() -> str:
    try:
        import streamlit as st

        sync_api_base_session()
        v = (st.session_state.get("rag_api_base") or "").strip()
        if v:
            return v
    except Exception:
        pass
    return _env_api_base()


def get_api_auth_headers() -> dict[str, str]:
    try:
        import streamlit as st

        if hasattr(st, "session_state"):
            v = (st.session_state.get("rag_api_secret") or "").strip()
            if v:
                return {"X-API-Key": v}
    except Exception:
        pass
    for envk in ("STREAMLIT_RAG_API_SECRET", "RAG_API_SECRET"):
        v = os.environ.get(envk, "").strip()
        if v:
            return {"X-API-Key": v}
    return {}


def http_client(
    base: str | None = None,
    timeout: float | httpx.Timeout = INGEST_TIMEOUT,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Client:
    url = (base or get_api_base()).rstrip("/")
    h = {**get_api_auth_headers(), **(extra_headers or {})}
    return httpx.Client(base_url=url, timeout=timeout, headers=h or None)


def _ensure_backend_silent(api_base: str) -> bool:
    """内部静默重试（3×3s），含鉴权探测。"""
    _api_src_on_path()
    try:
        from api.connectivity import check_api_with_retry

        ok, _ = check_api_with_retry(api_base, headers=get_api_auth_headers())
        return ok
    except Exception:
        try:
            with http_client(api_base, timeout=HEALTH_TIMEOUT) as c:
                if c.get("/health").status_code != 200:
                    return False
                r = c.get("/config/public")
                return r.status_code == 200
        except Exception:
            return False


def fetch_model_profiles(api_base: str | None = None) -> dict[str, Any] | None:
    base = api_base or get_api_base()
    try:
        with http_client(base, timeout=httpx.Timeout(5.0, connect=2.0)) as c:
            r = c.get("/config/model-profiles")
            if r.status_code == 200:
                return r.json()
            if r.status_code in (401, 403):
                return {"_auth_error": True}
    except Exception:
        return None
    return None


def ping_health_fast(api_base: str | None = None) -> bool:
    base = api_base or get_api_base()
    try:
        with http_client(base, timeout=HEALTH_TIMEOUT) as c:
            return c.get("/health").status_code == 200
    except Exception:
        return False


def profile_labels(data: dict[str, Any] | None) -> list[tuple[str, str]]:
    head = [
        ("使用服务器默认的大模型设置", ""),
        ("不使用已保存的接入，仅用服务器环境变量里的密钥", "__env__"),
    ]
    if not data or data.get("_auth_error"):
        return head
    rows = data.get("profiles") or []
    default_id = data.get("default_profile_id") or ""
    out: list[tuple[str, str]] = list(head)
    for p in rows:
        pid = str(p.get("id", ""))
        name = str(p.get("name", pid))
        vendor = str(p.get("vendor", ""))
        hint = "已保存密钥" if p.get("has_api_key") else "未配置密钥"
        suffix = " ★" if pid and pid == str(default_id) else ""
        out.append((f"{name} ({vendor}) — {hint}{suffix}", pid))
    return out
