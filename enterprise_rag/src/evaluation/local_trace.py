"""Trace configuration: local JSONL + optional Langfuse."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import settings
from evaluation.langfuse_trace import langfuse_status, langfuse_trace_url


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


def _build_hints(*, local_enabled: bool, langfuse_on: bool) -> list[str]:
    hints: list[str] = []
    if langfuse_on:
        hints.append("Langfuse：已开启；在 Langfuse UI 按 session/user 查看完整 trace 树")
        sample = langfuse_trace_url("YOUR_TRACE_ID")
        if sample:
            hints.append(f"Trace 链接格式：{sample.replace('YOUR_TRACE_ID', '<trace_id>')}")
    elif langfuse_status().get("langfuse_tracing"):
        hints.append("Langfuse：设置 LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY 并 pip install langfuse")
    if local_enabled:
        hints.append("本地 JSONL：/chat/stream 写入 chat_trace.jsonl；Admin 反馈「查看链路」可回放")
    else:
        hints.append("本地 JSONL：LOCAL_TRACE_ENABLED=true 可启用 Admin 反馈链路详情")
    hints.append("DeerFlow task/auto（8011）：同一套 LANGFUSE_* 变量，lead agent 自动上报 LangGraph")
    return hints


def tracing_active() -> bool:
    return bool(settings.local_trace_enabled) or bool(langfuse_status().get("langfuse_enabled"))


def get_trace_status() -> dict[str, Any]:
    local_path = _local_trace_path()
    local_enabled = bool(settings.local_trace_enabled)
    lf = langfuse_status()
    langfuse_on = bool(lf.get("langfuse_enabled"))
    backends: list[str] = []
    if local_enabled:
        backends.append("local_jsonl")
    if langfuse_on:
        backends.append("langfuse")
    backend = "+".join(backends) if backends else "off"

    return {
        "backend": backend,
        "local_enabled": local_enabled,
        "local_trace_enabled": local_enabled,
        "local_path": str(local_path),
        "local_trace_file": str(local_path),
        "local_file_exists": local_path.is_file(),
        "local_record_count": _local_record_count(local_path),
        "local_trace_lines": _local_record_count(local_path),
        "active": tracing_active(),
        **lf,
        "hints": _build_hints(local_enabled=local_enabled, langfuse_on=langfuse_on),
    }


def configure_tracing() -> dict[str, Any]:
    """Startup hook — ensure JSONL dir exists; warm Langfuse client when configured."""
    if settings.local_trace_enabled:
        _local_trace_path().parent.mkdir(parents=True, exist_ok=True)
    from evaluation.langfuse_trace import get_langfuse_client

    get_langfuse_client()
    return get_trace_status()
