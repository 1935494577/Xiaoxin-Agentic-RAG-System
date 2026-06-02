from __future__ import annotations

from typing import Any


def format_context_with_meta(meta: dict[str, Any]) -> str:
    """Prepend ingest tags so the LLM can answer metadata questions."""
    text = str(meta.get("text") or "").strip()
    tags: list[str] = []
    if meta.get("source"):
        tags.append(f"来源={meta['source']}")
    if meta.get("department"):
        tags.append(f"部门={meta['department']}")
    if meta.get("permission_label"):
        tags.append(f"标签={meta['permission_label']}")
    if tags:
        return f"[{' | '.join(tags)}]\n{text}"
    return text


def format_source_citation(meta: dict[str, Any]) -> str:
    src = str(meta.get("source") or "")
    pid = str(meta.get("parent_id") or "")
    base = f"{src}#{pid}" if pid else src
    extras: list[str] = []
    if meta.get("department"):
        extras.append(f"部门={meta['department']}")
    if meta.get("permission_label"):
        extras.append(f"标签={meta['permission_label']}")
    if extras:
        return f"{base} ({', '.join(extras)})"
    return base


def source_ref_dict(meta: dict[str, Any]) -> dict[str, str]:
    return {
        "source": str(meta.get("source") or ""),
        "parent_id": str(meta.get("parent_id") or ""),
        "department": str(meta.get("department") or ""),
        "permission_label": str(meta.get("permission_label") or ""),
    }
