"""Tests for deterministic org-chart parsing at ingest."""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE = Path(r"d:\dataset\科技公司关系图测试.txt")
SAMPLE_TEXT = SAMPLE.read_text(encoding="utf-8") if SAMPLE.is_file() else """
张振国（CEO）：管辖 CTO、CFO、COO、战略顾问
林雪（CTO）：向 CEO 汇报；管辖 后端负责人、前端负责人
李浩然（后端负责人）：向 CTO 汇报；管辖 高级后端工程师
刘洋（高级后端工程师）：向 后端负责人 汇报
"""


@pytest.fixture
def graph_db(tmp_path, monkeypatch):
    db = tmp_path / "org_chart.db"
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    yield db
    monkeypatch.setattr("graph.store._conn", None)


def test_parse_org_chart_text():
    from graph.org_chart import parse_org_chart_text

    people, rels = parse_org_chart_text(SAMPLE_TEXT)
    names = {p["name"] for p in people}
    assert "张振国" in names
    assert "林雪" in names
    assert "刘洋" in names
    assert any(r["from_name"] == "林雪" and r["to_name"] == "张振国" for r in rels)
    if "刘洋" in names:
        assert any(r["from_name"] == "刘洋" and r["to_name"] == "李浩然" for r in rels)


def test_parse_org_chart_extracts_bio():
    from graph.org_chart import parse_org_chart_text

    text = """
林峰（CTO）：向 CEO 汇报；管辖 研发部、架构组；负责技术路线与架构决策
王鑫（COO）：向 CEO 汇报；负责日常运营与交付管理
张振国（CEO）：管辖 CTO、CFO、COO；负责公司战略与投融资
"""
    people, _rels = parse_org_chart_text(text)
    by_name = {p["name"]: p for p in people}
    assert by_name["林峰"]["bio"] == "负责技术路线与架构决策"
    assert by_name["王鑫"]["bio"] == "负责日常运营与交付管理"
    assert by_name["张振国"]["bio"] == "负责公司战略与投融资"


def test_import_org_chart_persists_bio_in_viz(graph_db):
    from graph.org_chart import import_org_chart_if_detected
    from graph.viz import build_graph_viz

    text = "张振国（CEO）：管辖 CTO\n林峰（CTO）：向 CEO 汇报；负责技术路线与架构决策"
    import_org_chart_if_detected(text, source="bio_test.txt", department="技术部")
    viz = build_graph_viz(center="林峰", department="技术部", max_hops=2, limit=20)
    node = next(n for n in viz["nodes"] if n["label"] == "林峰")
    assert "技术路线" in node["bio"]


def test_import_org_chart_if_detected(graph_db):
    from graph.org_chart import import_org_chart_if_detected
    from graph.viz import build_graph_viz

    counts = import_org_chart_if_detected(
        SAMPLE_TEXT,
        source="科技公司关系图测试.txt",
        department="技术部",
    )
    assert counts is not None
    pc, ec = counts
    assert pc >= 5
    assert ec >= 5

    viz = build_graph_viz(center="张振国", department="技术部", max_hops=2, limit=60)
    assert len(viz["nodes"]) >= 5
    assert len(viz["edges"]) >= 5
