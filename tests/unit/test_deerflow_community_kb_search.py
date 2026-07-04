"""deerflow_community.kb_search tool factory."""

from __future__ import annotations

from deerflow_community.kb_search import KbSearchInput, kb_search_tool


def test_kb_search_tool_name_and_schema():
    tool = kb_search_tool()
    assert tool.name == "kb_search"
    assert tool.args_schema is KbSearchInput
