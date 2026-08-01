"""Langfuse v4 tracing helpers — aligned with DeerFlow env vars."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

from config import settings

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_flag(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in _TRUTHY


def _first_env(*names: str) -> str:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def langfuse_tracing_flag_on() -> bool:
    if _env_flag("LANGFUSE_TRACING"):
        return True
    return bool(settings.langfuse_tracing)


def langfuse_credentials_configured() -> bool:
    pub = (_first_env("LANGFUSE_PUBLIC_KEY") or settings.langfuse_public_key or "").strip()
    sec = (_first_env("LANGFUSE_SECRET_KEY") or settings.langfuse_secret_key or "").strip()
    return bool(pub and sec)


def langfuse_package_installed() -> bool:
    try:
        import langfuse  # noqa: F401

        return True
    except ImportError:
        return False


def langfuse_enabled() -> bool:
    return langfuse_tracing_flag_on() and langfuse_credentials_configured() and langfuse_package_installed()


def langfuse_host() -> str:
    host = (_first_env("LANGFUSE_BASE_URL") or settings.langfuse_base_url or "").strip()
    return host.rstrip("/") or "https://cloud.langfuse.com"


def get_langfuse_client() -> Any | None:
    if not langfuse_enabled():
        return None
    try:
        from langfuse import Langfuse, get_client

        pub = (_first_env("LANGFUSE_PUBLIC_KEY") or settings.langfuse_public_key).strip()
        sec = (_first_env("LANGFUSE_SECRET_KEY") or settings.langfuse_secret_key).strip()
        host = langfuse_host()
        Langfuse(public_key=pub, secret_key=sec, host=host)
        return get_client(public_key=pub)
    except Exception:
        return None


def langfuse_trace_url(trace_id: str | None) -> str | None:
    tid = (trace_id or "").strip()
    if not tid or not langfuse_enabled():
        return None
    return f"{langfuse_host()}/trace/{quote(tid, safe='')}"


def flush_langfuse() -> None:
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        pass


def langfuse_status() -> dict[str, Any]:
    flag = langfuse_tracing_flag_on()
    creds = langfuse_credentials_configured()
    pkg = langfuse_package_installed()
    enabled = langfuse_enabled()
    return {
        "langfuse_enabled": enabled,
        "langfuse_tracing": flag,
        "langfuse_configured": creds,
        "langfuse_package_installed": pkg,
        "langfuse_host": langfuse_host(),
        "langfuse_ui_hint": langfuse_trace_url("example") if enabled else None,
    }
