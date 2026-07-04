"""Tests for multi-line / dotted / collaboration org-chart parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

DEEP_SAMPLE = Path(r"d:\dataset\深层公司关系.txt")

MULTILINE_BLOCK = """
张振国（CEO）：全面负责公司战略与运营
直接管辖：CTO、CFO、COO、战略顾问
每周主持高管例会，最终审批预算与战略决策
虚线指导：产品总监（重大研发方向需CEO终审）

林雪（CTO）：向 CEO 汇报
管辖：后端负责人、前端负责人、DevOps经理
虚线管辖：产品总监（技术可行性评审需CTO签字）

高飞（产品总监）：向 COO 汇报

李浩然（后端负责人）：向 CTO 汇报
协作关系：与前端负责人每周对接接口规范，与AI实验室对接模型部署
"""

BILATERAL = """
【外部对接与项目协作关系】
战略顾问 ↔ AI实验室负责人：每月一次前沿技术研讨会
后端负责人 ↔ AI实验室负责人：模型部署与性能优化周会
"""


@pytest.fixture
def graph_db(tmp_path, monkeypatch):
    db = tmp_path / "deep_org.db"
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    yield db
    monkeypatch.setattr("graph.store._conn", None)


def test_multiline_manage_and_dotted():
    from graph.org_chart import parse_org_chart_text

    people, rels = parse_org_chart_text(MULTILINE_BLOCK)
    names = {p["name"] for p in people}
    assert {"张振国", "林雪", "李浩然", "高飞"}.issubset(names)

    zhang = next(p for p in people if p["name"] == "张振国")
    assert "全面负责" in zhang["bio"]
    assert "每周主持高管例会" in zhang["bio"]

    manage = [r for r in rels if r["relation"] == "管辖" and r["from_name"] == "张振国"]
    assert len(manage) >= 1
    assert any(r["to_name"] == "林雪" for r in manage)

    dotted = [r for r in rels if r["relation"] == "虚线指导" and r["from_name"] == "张振国"]
    assert any(r["to_name"] == "高飞" for r in dotted)

    dotted_manage = [r for r in rels if r["relation"] == "虚线管辖" and r["from_name"] == "林雪"]
    assert any(r["to_name"] == "高飞" for r in dotted_manage)

    lin_manage = [r for r in rels if r["relation"] == "管辖" and r["from_name"] == "林雪"]
    assert any(r["to_name"] == "李浩然" for r in lin_manage)

    li = next(p for p in people if p["name"] == "李浩然")
    assert "协作关系" in li["bio"] or "前端负责人" in li["bio"]


def test_bilateral_collaboration_edges():
    from graph.org_chart import parse_org_chart_text

    text = """
赵远（战略顾问）：向 CEO 汇报
吴迪（AI实验室负责人）：向 CTO 汇报
李浩然（后端负责人）：向 CTO 汇报
""" + BILATERAL
    people, rels = parse_org_chart_text(text)
    collab = [r for r in rels if r["relation"] == "协作"]
    assert len(collab) >= 2
    assert any(
        r["from_name"] == "赵远" and r["to_name"] == "吴迪" for r in collab
    ) or any(r["from_name"] == "吴迪" and r["to_name"] == "赵远" for r in collab)


def test_skips_headcount_placeholders():
    from graph.org_chart import parse_org_chart_text

    text = """
李浩然（后端负责人）：向 CTO 汇报
管辖：高级后端工程师×2、后端工程师×1
韩璐（数据标注组长）：向 AI实验室负责人 汇报；管辖 数据标注员×3
"""
    _people, rels = parse_org_chart_text(text)
    bad_targets = [r["to_name"] for r in rels if "×" in r["to_name"]]
    assert bad_targets == []


@pytest.mark.skipif(not DEEP_SAMPLE.is_file(), reason="deep sample file not on disk")
def test_deep_company_file_parses_rich_graph():
    from graph.org_chart import parse_org_chart_text

    text = DEEP_SAMPLE.read_text(encoding="utf-8")
    people, rels = parse_org_chart_text(text)
    assert len(people) >= 36
    assert len(rels) >= 60

    rel_types = {r["relation"] for r in rels}
    assert "管辖" in rel_types
    assert "汇报" in rel_types
    assert "协作" in rel_types or "虚线管辖" in rel_types or "虚线指导" in rel_types

    zhang = next(p for p in people if p["name"] == "张振国")
    assert "全面负责" in zhang["bio"]
    assert len([r for r in rels if r["from_name"] == "张振国" and r["relation"] == "管辖"]) >= 3


def test_import_deep_sample(graph_db):
    from graph.org_chart import import_org_chart_if_detected
    from graph.viz import build_graph_viz

    text = MULTILINE_BLOCK + BILATERAL.replace("战略顾问", "赵远").replace("AI实验室负责人", "吴迪")
    counts = import_org_chart_if_detected(text, source="deep_test.txt", department="技术部")
    assert counts is not None
    pc, ec = counts
    assert pc >= 3
    assert ec >= 4

    viz = build_graph_viz(center="张振国", department="技术部", max_hops=3, limit=100)
    assert len(viz["edges"]) >= 4
    edge_labels = {e["label"] for e in viz["edges"]}
    assert "管辖" in edge_labels
