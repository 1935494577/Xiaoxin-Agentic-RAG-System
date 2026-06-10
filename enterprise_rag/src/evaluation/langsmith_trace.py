"""LangSmith / LangChain tracing (optional, driven by env)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from config import settings


def _langsmith_api_key_configured() -> bool:
    key = (os.environ.get("LANGCHAIN_API_KEY") or settings.langchain_api_key or "").strip()
    return bool(key)


def _langsmith_tracing_flag_on() -> bool:
    raw = (os.environ.get("LANGCHAIN_TRACING_V2") or "").strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    return bool(settings.langchain_tracing_v2)


def _langsmith_enabled() -> bool:
    return _langsmith_tracing_flag_on() and _langsmith_api_key_configured()


def _langsmith_package_installed() -> bool:
    try:
        import langsmith  # noqa: F401

        return True
    except ImportError:
        return False


def _local_trace_path() -> Path:
    return Path(settings.chat_trace_path)


def _local_record_count(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def _build_hints(
    *,
    langsmith_flag: bool,
    langsmith_key: bool,
    langsmith_pkg: bool,
    local_enabled: bool,
) -> list[str]:
    hints: list[str] = []
    if not langsmith_flag:
        hints.append("LangSmith：在 .env 设置 LANGCHAIN_TRACING_V2=true 并重启 API")
    if not langsmith_key:
        hints.append("LangSmith：在 .env 设置 LANGCHAIN_API_KEY=lsv2_...")
    if langsmith_flag and langsmith_key and not langsmith_pkg:
        hints.append("LangSmith：执行 pip install langsmith")
    if local_enabled:
        hints.append("本地 JSONL：已开启，对话链路将追加写入 chat_trace.jsonl")
    else:
        hints.append("本地 JSONL：尚未开启（可在 .env 设置 LOCAL_TRACE_ENABLED=true，第三步将接入写入）")
    return hints


def tracing_active() -> bool:
    return _langsmith_enabled() or bool(settings.local_trace_enabled)


def get_trace_status() -> dict[str, Any]:
    project = (settings.langchain_project or os.environ.get("LANGCHAIN_PROJECT") or "").strip()
    local_path = _local_trace_path()
    local_enabled = bool(settings.local_trace_enabled)
    langsmith_flag = _langsmith_tracing_flag_on()
    langsmith_key = _langsmith_api_key_configured()
    langsmith_pkg = _langsmith_package_installed()
    langsmith_on = _langsmith_enabled()

    return {
        "langsmith_enabled": langsmith_on,
        "langsmith_configured": langsmith_key,
        "langsmith_tracing_v2": langsmith_flag,
        "langsmith_package_installed": langsmith_pkg,
        "local_enabled": local_enabled,
        "local_path": str(local_path),
        "local_file_exists": local_path.is_file(),
        "local_record_count": _local_record_count(local_path),
        "project": project,
        "active": tracing_active(),
        "hints": _build_hints(
            langsmith_flag=langsmith_flag,
            langsmith_key=langsmith_key,
            langsmith_pkg=langsmith_pkg,
            local_enabled=local_enabled,
        ),
    }


def configure_tracing() -> dict[str, Any]:
    if _langsmith_tracing_flag_on():
        _langsmith_package_installed()
    return get_trace_status()
