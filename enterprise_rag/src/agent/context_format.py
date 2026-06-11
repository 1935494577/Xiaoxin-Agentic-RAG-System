from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any


def source_basename(source: str) -> str:
    """Normalize ingest source to a stable filename key for citation dedup."""
    raw = (source or "").strip()
    if not raw:
        return ""
    primary = raw.split(" / ")[0].strip()
    name = PurePosixPath(primary.replace("\\", "/")).name
    return (name or primary).lower()


def _meta_score(meta: dict[str, Any]) -> float:
    for key in ("rerank_score", "hybrid_score", "score"):
        val = meta.get(key)
        if val is None:
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return 0.0


def dedupe_citation_metas(metas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One citation row per source file; keep the highest-scored parent chunk."""
    best: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for meta in metas:
        pid = str(meta.get("parent_id") or "").strip()
        src = str(meta.get("source") or "").strip()
        if not pid and not src:
            continue
        key = source_basename(src) or pid
        if key not in best:
            best[key] = meta
            order.append(key)
            continue
        if _meta_score(meta) > _meta_score(best[key]):
            best[key] = meta
    return [best[k] for k in order]


def build_source_citations(metas: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, str]]]:
    """Dedupe by source file, then format for API/SSE payloads."""
    refs = dedupe_citation_metas([m for m in metas if m.get("parent_id") or m.get("source")])
    sources = [format_source_citation(m) for m in refs]
    source_refs = [source_ref_dict(m) for m in refs]
    return sources, source_refs


def format_context_with_meta(meta: dict[str, Any]) -> str:
    """Prepend ingest tags so the LLM can answer metadata questions."""
    text = str(meta.get("text") or "").strip()
    tags: list[str] = []
    if meta.get("source"):
        tags.append(f"来源={meta['source']}")
    if meta.get("department"):
        tags.append(f"部门={meta['department']}")
    if meta.get("permission_label"):
        vis = str(meta["permission_label"])
        label = {"public": "公开", "internal": "内部", "confidential": "机密"}.get(vis, vis)
        tags.append(f"可见范围={label}")
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
        vis = str(meta["permission_label"])
        label = {"public": "公开", "internal": "内部", "confidential": "机密"}.get(vis, vis)
        extras.append(f"可见范围={label}")
    if extras:
        return f"{base} ({', '.join(extras)})"
    return base


def source_ref_dict(meta: dict[str, Any]) -> dict[str, str]:
    src = str(meta.get("source") or "")
    display = source_basename(src) or src
    return {
        "source": display,
        "parent_id": str(meta.get("parent_id") or ""),
        "department": str(meta.get("department") or ""),
        "permission_label": str(meta.get("permission_label") or ""),
    }
