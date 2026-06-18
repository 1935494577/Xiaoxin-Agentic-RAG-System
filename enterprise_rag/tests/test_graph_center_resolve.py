"""Test center resolution from document source keywords."""

from __future__ import annotations

import pytest


@pytest.fixture
def graph_db(tmp_path, monkeypatch):
    db = tmp_path / "center.db"
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    yield db
    monkeypatch.setattr("graph.store._conn", None)


def test_resolve_center_from_source_keyword(graph_db):
    from graph.org_chart import import_org_chart_if_detected
    from graph.viz import resolve_center_from_query

    text = """
张振国（CEO）：管辖 CTO、CFO
林雪（CTO）：向 CEO 汇报
"""
    import_org_chart_if_detected(text, source="科技公司关系图测试.txt", department="技术部")
    center = resolve_center_from_query("给我展示一下科技公司关系图", department="技术部")
    assert center == "张振国"


def test_resolve_generic_company_relation_queries(graph_db):
    from graph.org_chart import import_org_chart_if_detected
    from graph.viz import resolve_center_from_query

    text = """
张振国（CEO）：管辖 林雪
林雪（CTO）：向 CEO 汇报
"""
    import_org_chart_if_detected(text, source="科技公司关系图测试.txt", department="技术部")

    assert resolve_center_from_query("展示一下公司关系", department="技术部") == "张振国"
    assert resolve_center_from_query("展示一下科技公司的公司关系", department="技术部") == "张振国"
    assert resolve_center_from_query("公司所有的关系网", department="技术部") == "张振国"


def test_show_relationship_graph_generic_query(graph_db):
    from agent.tools.builtins.relationship_graph import (
        clear_relationship_graph_context,
        set_relationship_graph_context,
        show_relationship_graph,
    )
    from graph.org_chart import import_org_chart_if_detected
    from graph.viz import parse_graph_viz_from_tool_output

    text = "张振国（CEO）：管辖 林雪\n林雪（CTO）：向 CEO 汇报"
    import_org_chart_if_detected(text, source="科技公司关系图测试.txt", department="技术部")
    set_relationship_graph_context(user_department="技术部", max_hops=3)
    try:
        out = show_relationship_graph(query="展示一下公司关系")
        assert "请提供" not in out
        viz = parse_graph_viz_from_tool_output(out)
        assert viz is not None
        assert len(viz.get("edges") or []) >= 1
    finally:
        clear_relationship_graph_context()
