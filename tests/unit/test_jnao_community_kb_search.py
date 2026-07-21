"""jnao_community.kb_search LangChain tool."""

from __future__ import annotations

from jnao_community.kb_search import kb_search_tool


def test_kb_search_tool_name_and_schema():
    assert kb_search_tool.name == "kb_search"
    assert kb_search_tool.args_schema is not None
    props = kb_search_tool.args_schema.schema().get("properties") or {}
    assert "query" in props
    assert "top_k" in props
