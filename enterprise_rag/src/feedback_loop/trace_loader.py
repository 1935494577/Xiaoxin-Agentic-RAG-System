"""Load trace runs from local JSONL by trace_id."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings


def _trace_path() -> Path:
    return Path(settings.chat_trace_path)


def load_trace_by_id(trace_id: str) -> dict[str, Any] | None:
    tid = (trace_id or "").strip()
    if not tid:
        return None
    path = _trace_path()
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(obj.get("trace_id") or "") == tid:
                    return obj
    except OSError:
        return None
    return None


def snapshot_from_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Extract context_count, sources, and a trimmed snapshot for feedback enrichment."""
    context_count: int | None = None
    sources: list[str] = []
    seen: set[str] = set()

    for sp in trace.get("spans") or []:
        if not isinstance(sp, dict):
            continue
        name = str(sp.get("name") or "")
        stype = str(sp.get("type") or "")
        if name != "retrieve" and stype not in ("retrieval",):
            continue
        output = sp.get("output") or {}
        if isinstance(output, dict) and "result" in output:
            inner = output.get("result")
            if isinstance(inner, dict):
                output = inner
        if not isinstance(output, dict):
            continue
        if context_count is None and output.get("context_count") is not None:
            try:
                context_count = int(output["context_count"])
            except (TypeError, ValueError):
                pass
        for row in output.get("contexts_meta") or []:
            if not isinstance(row, dict):
                continue
            src = str(row.get("source") or "").strip()
            if src and src not in seen:
                seen.add(src)
                sources.append(src)
        break

    trimmed_spans = []
    for sp in (trace.get("spans") or [])[:6]:
        if isinstance(sp, dict):
            trimmed_spans.append(
                {
                    "type": sp.get("type"),
                    "name": sp.get("name"),
                    "status": sp.get("status"),
                    "latency_ms": sp.get("latency_ms"),
                    "output": sp.get("output"),
                }
            )

    snapshot = {
        "trace_id": trace.get("trace_id"),
        "question": trace.get("question"),
        "answer_mode": trace.get("answer_mode"),
        "meta": trace.get("meta"),
        "spans": trimmed_spans,
    }
    return {
        "context_count": context_count,
        "sources": sources,
        "trace_snapshot": snapshot,
        "question": str(trace.get("question") or "").strip() or None,
        "answer_mode": str(trace.get("answer_mode") or "").strip() or None,
    }
