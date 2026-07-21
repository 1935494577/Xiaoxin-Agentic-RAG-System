"""Jnao gateway dependencies for Jnao (reads FastAPI app.state)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request

if TYPE_CHECKING:
    from deerflow.config.app_config import AppConfig


def get_config() -> AppConfig:
    try:
        from deerflow.config.app_config import get_app_config

        return get_app_config()
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Agent harness not installed") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Configuration not available") from exc


def _require_state(request: Request, attr: str, label: str):
    val = getattr(request.app.state, attr, None)
    if val is None:
        raise HTTPException(status_code=503, detail=f"{label} not available")
    return val


def get_run_store(request: Request):
    return _require_state(request, "run_store", "Run store")


def get_stream_bridge(request: Request):
    return _require_state(request, "stream_bridge", "Stream bridge")


def get_run_manager(request: Request):
    return _require_state(request, "run_manager", "Run manager")
