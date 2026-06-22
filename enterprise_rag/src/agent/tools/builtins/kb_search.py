"""Knowledge base search tool for Agentic RAG."""

from __future__ import annotations

from typing import Any

_context: dict[str, Any] = {}


def set_kb_search_context(**kwargs: Any) -> None:
    _context.clear()
    _context.update(kwargs)


def clear_kb_search_context() -> None:
    _context.clear()


def get_kb_hits() -> list[dict[str, Any]]:
    return list(_context.get("hits") or [])


def kb_search(query: str, top_k: int | None = None) -> str:
    from retrieval.hybrid_searcher import hybrid_search

    q = (query or "").strip()
    if not q:
        return "请提供检索 query。"
    dept = str(_context.get("user_department") or "general")
    k = int(top_k) if top_k is not None else int(_context.get("top_k") or 5)
    allowed = _context.get("allowed_sources")

    _, parents = hybrid_search(
        q,
        dept,
        top_k=k,
        chat_model=_context.get("chat_model"),
        llm_api_base=_context.get("llm_api_base"),
        llm_api_key=_context.get("llm_api_key"),
        skip_query_rewrite=True,
        skip_rerank=bool(_context.get("skip_rerank")),
    )
    if allowed:
        allowed_set = set(allowed)
        parents = [p for p in parents if str(p.get("source") or "") in allowed_set]

    hits = _context.setdefault("hits", [])
    if not parents:
        return "知识库未检索到相关内容。"

    lines = [f"检索「{q}」共 {len(parents)} 条："]
    for i, p in enumerate(parents[:k], 1):
        text = str(p.get("text") or "")[:600]
        source = str(p.get("source") or "")
        score = p.get("hybrid_score") or p.get("rerank_score") or 0
        lines.append(f"{i}. [{source}] (score={score:.2f})\n{text}")
        hits.append(p)
    return "\n\n".join(lines)
