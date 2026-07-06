"""DF-1: kb_search tool wiring + business SKILL.md files."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

SAMPLE_PARENT = {
    "parent_id": "p-read-1",
    "text": "1-3年级超脑阅读训练每周不少于两次。",
    "source": "阅读制度.pdf",
    "hybrid_score": 0.88,
    "department": "运营部",
    "permission_label": "internal",
    "tags": [],
}


def _parse_skill_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert match, f"invalid frontmatter: {skill_md}"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


@pytest.fixture(autouse=True)
def _reset_kb_context():
    from jnao_community.kb_context import clear_kb_run_context

    clear_kb_run_context()
    yield
    clear_kb_run_context()


def test_kb_search_tool_is_langchain_tool_with_real_name():
    from jnao_community.kb_search import kb_search_tool

    assert kb_search_tool.name == "kb_search"
    assert "knowledge" in (kb_search_tool.description or "").lower()


@patch("retrieval.hybrid_searcher.hybrid_search")
def test_kb_search_tool_invoke_passes_department_and_query(mock_hs):
    from jnao_community.kb_context import bind_kb_run_context
    from jnao_community.kb_search import kb_search_tool

    bind_kb_run_context(user_department="运营部", top_k=5)
    mock_hs.return_value = ([], [SAMPLE_PARENT])

    out = kb_search_tool.invoke({"query": "超脑阅读训练要求", "top_k": 3})

    mock_hs.assert_called_once()
    assert mock_hs.call_args[0][0] == "超脑阅读训练要求"
    assert mock_hs.call_args[0][1] == "运营部"
    assert mock_hs.call_args[1]["top_k"] == 3
    assert "阅读制度.pdf" in out
    assert "超脑阅读" in out or "阅读" in out


@patch("retrieval.hybrid_searcher.hybrid_search")
def test_kb_search_tool_respects_allowed_sources(mock_hs):
    from jnao_community.kb_context import bind_kb_run_context
    from jnao_community.kb_search import kb_search_tool

    bind_kb_run_context(
        user_department="技术部",
        allowed_sources=["allowed.pdf"],
    )
    mock_hs.return_value = (
        [],
        [
            {**SAMPLE_PARENT, "source": "blocked.pdf"},
            {**SAMPLE_PARENT, "source": "allowed.pdf", "text": "可见内容"},
        ],
    )

    out = kb_search_tool.invoke({"query": "制度", "top_k": 5})

    assert "allowed.pdf" in out
    assert "blocked.pdf" not in out
    assert "可见内容" in out


def test_industry_research_skill_frontmatter_and_allowed_tools():
    skill_md = REPO_ROOT / "skills" / "public" / "industry-research" / "SKILL.md"
    assert skill_md.is_file()
    fm = _parse_skill_frontmatter(skill_md)
    assert fm["name"] == "industry-research"
    assert "web_search" in fm["allowed-tools"]
    assert "kb_search" in fm["allowed-tools"]


def test_wecom_parent_dm_skill_frontmatter_and_allowed_tools():
    skill_md = REPO_ROOT / "skills" / "public" / "wecom-parent-dm" / "SKILL.md"
    assert skill_md.is_file()
    fm = _parse_skill_frontmatter(skill_md)
    assert fm["name"] == "wecom-parent-dm"
    tools = fm["allowed-tools"]
    assert "kb_search" in tools
    assert "format_structured_output" in tools
