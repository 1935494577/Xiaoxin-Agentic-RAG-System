"""Tests for relationship graph visualization helpers."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def graph_db(tmp_path, monkeypatch):
    db = tmp_path / "viz_graph.db"
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    yield db
    monkeypatch.setattr("graph.store._conn", None)


def test_build_graph_viz_from_imported_bundle(graph_db):
    from graph.store import import_relationship_bundle
    from graph.viz import build_graph_viz, parse_graph_viz_from_tool_output, resolve_center_from_query

    import_relationship_bundle(
        source="org_test",
        department="技术部",
        people=[
            {"name": "张三", "title": "经理", "department": "技术部", "bio": "负责平台"},
            {"name": "李四", "title": "总监", "department": "技术部"},
            {"name": "王五", "title": "工程师", "department": "技术部"},
        ],
        relationships=[
            {"from_name": "张三", "relation": "上级", "to_name": "李四"},
            {"from_name": "王五", "relation": "汇报", "to_name": "张三"},
        ],
    )

    assert resolve_center_from_query("展示张三的上下级关系") == "张三"

    viz = build_graph_viz(center="张三", department="技术部", max_hops=2)
    assert viz["center_id"]
    assert len(viz["nodes"]) >= 3
    assert len(viz["edges"]) == 2
    assert any("张三" in line for line in viz["summary_lines"])

    from graph.viz import format_graph_tool_output

    raw = format_graph_tool_output(viz)
    assert "__GRAPH_VIZ_JSON__" in raw
    parsed = parse_graph_viz_from_tool_output(raw)
    assert parsed is not None
    assert len(parsed["nodes"]) == len(viz["nodes"])


def test_parse_graph_viz_invalid():
    from graph.viz import parse_graph_viz_from_tool_output

    assert parse_graph_viz_from_tool_output("no marker") is None
    assert parse_graph_viz_from_tool_output("__GRAPH_VIZ_JSON__\n{bad\n__END_GRAPH_VIZ__") is None


def test_show_relationship_graph_tool(graph_db):
    from agent.tools.builtins.relationship_graph import (
        clear_relationship_graph_context,
        set_relationship_graph_context,
        show_relationship_graph,
    )
    from graph.store import import_relationship_bundle
    from graph.viz import parse_graph_viz_from_tool_output

    import_relationship_bundle(
        source="tool_test",
        department="运营部",
        people=[{"name": "赵六", "title": "主管"}],
        relationships=[{"from_name": "赵六", "relation": "协作", "to_name": "钱七"}],
    )
    set_relationship_graph_context(user_department="运营部", max_hops=2)
    try:
        out = show_relationship_graph(query="赵六的工作关系", center_name="赵六")
        viz = parse_graph_viz_from_tool_output(out)
        assert viz is not None
        labels = {n["label"] for n in viz["nodes"]}
        assert "赵六" in labels
    finally:
        clear_relationship_graph_context()
