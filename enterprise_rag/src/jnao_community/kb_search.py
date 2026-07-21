"""kb_search LangChain tool — Jnao config `use: jnao_community.kb_search:kb_search_tool`."""

from __future__ import annotations

from langchain.tools import tool

from jnao_community.kb_context import apply_kb_run_context_to_legacy


@tool("kb_search", parse_docstring=True)
def kb_search_tool(query: str, top_k: int = 5) -> str:
    """Search the enterprise knowledge base.

    Args:
        query: Retrieval question or keywords.
        top_k: Number of chunks to return (1-10).
    """
    from agent.tools.builtins.kb_search import kb_search as legacy_kb_search

    q = (query or "").strip()
    if not q:
        return "请提供检索 query。"

    k = max(1, min(10, int(top_k)))
    apply_kb_run_context_to_legacy()
    return legacy_kb_search(q, top_k=k)
