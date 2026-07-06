"""list_kb_sources LangChain tool — Jnao config `use: jnao_community.list_kb_sources:list_kb_sources_tool`."""

from __future__ import annotations

from langchain.tools import tool


@tool("list_kb_sources", parse_docstring=True)
def list_kb_sources_tool(limit: int = 30) -> str:
    """List ingested knowledge-base document sources.

    Args:
        limit: Maximum number of sources to return (1-100).
    """
    from agent.tools.builtins.list_kb_sources import list_kb_sources

    k = max(1, min(100, int(limit)))
    return list_kb_sources(limit=k)
