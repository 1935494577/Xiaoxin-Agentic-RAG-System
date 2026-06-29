"""Org chart source supersession: new detailed doc replaces prior imports."""

from __future__ import annotations

import pytest


@pytest.fixture
def graph_db(tmp_path, monkeypatch):
    db = tmp_path / "org_chart.db"
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    yield db
    monkeypatch.setattr("graph.store._conn", None)


def test_new_org_chart_supersedes_other_sources(graph_db):
    from graph.org_chart import import_org_chart_if_detected
    from graph.store import list_org_chart_sources, _get_conn

    old = """张振国（CEO）：全面负责
管辖：林雪
林雪（CTO）：向 CEO 汇报
"""
    new = """张振国（CEO）：全面负责战略
管辖：林雪、陈雅文
林雪（CTO）：向 CEO 汇报
管辖：吴迪
吴迪（AI实验室负责人）：向 CTO 汇报
"""
    import_org_chart_if_detected(old, source="科技公司关系图测试.txt", department="技术部")
    import_org_chart_if_detected(new, source="深层公司关系.txt", department="技术部")

    sources = list_org_chart_sources(department="技术部")
    assert sources == ["深层公司关系.txt"]

    conn = _get_conn()
    old_edges = conn.execute(
        "SELECT COUNT(*) FROM edges WHERE source = ?", ("科技公司关系图测试.txt",)
    ).fetchone()[0]
    assert old_edges == 0
    new_edges = conn.execute(
        "SELECT COUNT(*) FROM edges WHERE source = ?", ("深层公司关系.txt",)
    ).fetchone()[0]
    assert new_edges >= 3
