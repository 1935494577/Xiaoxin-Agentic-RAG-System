from __future__ import annotations

from typing import Any


def filter_by_sources(contexts: list[dict[str, Any]], allowed_sources: list[str] | None) -> list[dict[str, Any]]:
    if allowed_sources is None:
        return contexts
    allow = set(allowed_sources)
    if not allow:
        return []
    return [c for c in contexts if (c.get("source") or "") in allow]
