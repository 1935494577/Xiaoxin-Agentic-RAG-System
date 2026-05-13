"""Shared helpers for Streamlit pages (import after sys.path includes this directory)."""

from __future__ import annotations

import os
from typing import Any

import httpx


# 与 README / 常见本地启动端口一致；仍可在侧栏或环境变量 RAG_API_BASE 中修改
DEFAULT_API = os.environ.get("RAG_API_BASE", "http://127.0.0.1:8001")


def get_api_auth_headers() -> dict[str, str]:
    """与 FastAPI 的 RAG_API_SECRET 对齐：优先本会话输入，其次环境变量。"""
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


def http_client(base: str, timeout: float = 300.0, extra_headers: dict[str, str] | None = None) -> httpx.Client:
    h = {**get_api_auth_headers(), **(extra_headers or {})}
    return httpx.Client(base_url=base.rstrip("/"), timeout=timeout, headers=h or None)


def fetch_model_profiles(api_base: str) -> dict[str, Any] | None:
    try:
        with http_client(api_base, timeout=20.0) as c:
            r = c.get("/config/model-profiles")
            if r.status_code == 200:
                return r.json()
    except Exception:
        return None
    return None


def profile_labels(data: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Return [(label, id), ...] for selectbox."""
    head = [
        ("使用服务器默认的大模型设置", ""),
        ("不使用已保存的接入，仅用服务器环境变量里的密钥", "__env__"),
    ]
    if not data:
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
