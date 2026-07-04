"""kb_search LangChain tool for DeerFlow `get_available_tools()` (DF-1 implements body)."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class KbSearchInput(BaseModel):
    query: str = Field(description="检索问句或关键词")
    top_k: int = Field(default=5, ge=1, le=10, description="返回条数，1-10")


def _kb_search_impl(query: str, top_k: int = 5) -> str:
    # DF-1: wire to existing agent.tools.builtins.kb_search
    from agent.tools.builtins.kb_search import kb_search as _legacy

    return _legacy(query, top_k=top_k)


def kb_search_tool() -> StructuredTool:
    """Entry point referenced by config.yaml: `use: ...kb_search:kb_search_tool`."""
    return StructuredTool.from_function(
        func=_kb_search_impl,
        name="kb_search",
        description="检索企业内部知识库。调查、分析类问题应先调用此工具。",
        args_schema=KbSearchInput,
    )
