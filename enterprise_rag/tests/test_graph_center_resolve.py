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
    center = resolve_center_from_query("给我展示一下科技公司关系图")
    assert center == "张振国"
