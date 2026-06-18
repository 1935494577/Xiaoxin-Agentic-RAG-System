"""Tests for deterministic org graph markdown summary."""

from __future__ import annotations


def test_build_org_graph_markdown_includes_structure_and_table():
    from graph.summary import build_org_graph_markdown

    viz = {
        "center_id": "a",
        "nodes": [
            {"id": "a", "label": "张振国", "title": "CEO", "bio": "全面负责公司战略"},
            {"id": "b", "label": "林雪", "title": "CTO", "bio": ""},
        ],
        "edges": [
            {"from": "b", "to": "a", "from_label": "林雪", "to_label": "张振国", "label": "汇报"},
            {"from": "a", "to": "b", "from_label": "张振国", "to_label": "林雪", "label": "管辖"},
            {"from": "b", "to": "c", "from_label": "林雪", "to_label": "李浩然", "label": "协作"},
            {"from": "c", "to": "b", "from_label": "李浩然", "to_label": "林雪", "label": "协作"},
        ],
    }
    md = build_org_graph_markdown(viz)
    assert "组织架构概览" in md
    assert "张振国" in md
    assert "协作关系" in md
    assert "李浩然" in md
