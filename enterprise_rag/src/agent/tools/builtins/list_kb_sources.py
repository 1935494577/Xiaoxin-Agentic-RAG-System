"""List ingested KB document sources for agent grounding."""

from __future__ import annotations

import json

from indexing.document_registry import get_document_registry


def list_kb_sources(*, limit: int = 30) -> str:
    reg = get_document_registry()
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for doc in (reg._docs or {}).values():  # noqa: SLF001
        src = str(doc.get("canonical_source") or "")
        if not src or src in seen:
            continue
        seen.add(src)
        rows.append(
            {
                "source": src,
                "parent_count": int(doc.get("parent_count") or 0),
                "child_count": int(doc.get("child_count") or 0),
            }
        )
    rows.sort(key=lambda r: str(r["source"]))
    if limit > 0:
        rows = rows[:limit]
    if not rows:
        return "知识库暂无已登记文档。请先在管理后台入库。"
    return json.dumps({"count": len(rows), "sources": rows}, ensure_ascii=False, indent=2)
