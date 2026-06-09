"""LangSmith / LangChain tracing (optional, driven by env)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from config import settings

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _langsmith_enabled() -> bool:
    v = (os.environ.get("LANGCHAIN_TRACING_V2") or "").strip().lower()
    if v not in ("true", "1", "yes"):
        return False
    key = (os.environ.get("LANGCHAIN_API_KEY") or settings.langchain_api_key or "").strip()
    return bool(key)


def tracing_active() -> bool:
    return _langsmith_enabled()


def get_trace_status() -> dict[str, Any]:
    project = (settings.langchain_project or os.environ.get("LANGCHAIN_PROJECT") or "").strip()
    return {
        "langsmith_enabled": _langsmith_enabled(),
        "local_enabled": False,
        "local_path": str(_REPO_ROOT / "enterprise_rag" / "data" / "chat_trace.jsonl"),
        "project": project,
        "active": tracing_active(),
    }


def configure_tracing() -> dict[str, Any]:
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1", "yes"):
        try:
            import langsmith  # noqa: F401
        except ImportError:
            pass
    return get_trace_status()
