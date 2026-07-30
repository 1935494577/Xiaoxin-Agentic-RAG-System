"""DF-3: jnao_community tools registered in config.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

RAG_TOOLS = (
    "kb_search",
    "list_kb_sources",
    "format_structured_output",
    "present_exam_paper",
    "search_exam_papers",
)

def _load_config() -> dict:
    data = yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _tool_names(cfg: dict) -> set[str]:
    return {t["name"] for t in (cfg.get("tools") or []) if isinstance(t, dict) and t.get("name")}


def test_config_registers_all_rag_community_tools():
    names = _tool_names(_load_config())
    for name in RAG_TOOLS:
        assert name in names


def test_list_kb_sources_tool_name_and_invoke():
    from jnao_community.list_kb_sources import list_kb_sources_tool

    assert list_kb_sources_tool.name == "list_kb_sources"
    out = list_kb_sources_tool.invoke({"limit": 5})
    assert isinstance(out, str)
    assert "知识库" in out or "sources" in out or "count" in out


def test_format_structured_output_tool_unknown_schema():
    from jnao_community.format_structured_output import format_structured_output_tool

    assert format_structured_output_tool.name == "format_structured_output"
    raw = format_structured_output_tool.invoke({"content": "draft", "schema_id": "not_a_schema"})
    assert "not_a_schema" in raw or "error" in raw.lower()


def test_present_exam_paper_tool_missing_id():
    from jnao_community.present_exam_paper import present_exam_paper_tool

    assert present_exam_paper_tool.name == "present_exam_paper"
    raw = present_exam_paper_tool.invoke({"source_paper_id": ""})
    assert "missing" in raw.lower() or "error" in raw.lower()


def test_search_exam_papers_tool_missing_query():
    from jnao_community.search_exam_papers import search_exam_papers_tool

    assert search_exam_papers_tool.name == "search_exam_papers"
    raw = search_exam_papers_tool.invoke({"query": ""})
    assert "missing" in raw.lower() or "error" in raw.lower()


@pytest.mark.harness
def test_harness_get_available_tools_includes_rag_tools():
    pytest.importorskip("deerflow")
    from deerflow.config.app_config import AppConfig
    from deerflow.tools import get_available_tools

    cfg = AppConfig.from_file(str(REPO_ROOT / "config.yaml"))
    names = {t.name for t in get_available_tools(app_config=cfg, include_mcp=False, subagent_enabled=False)}
    for name in RAG_TOOLS:
        assert name in names
