"""Lazy rebuild org chart from disk when graph edges missing."""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE = Path(r"d:\dataset\科技公司关系图测试.txt")
TEXT = (
    SAMPLE.read_text(encoding="utf-8")
    if SAMPLE.is_file()
    else """
张振国（CEO）：管辖 CTO、CFO
林雪（CTO）：向 CEO 汇报
"""
)


@pytest.fixture
def graph_env(tmp_path, monkeypatch):
    db = tmp_path / "lazy.db"
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "科技公司关系图测试.txt").write_text(TEXT, encoding="utf-8")
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    monkeypatch.setattr("config.settings.data_processed_dir", processed)
    monkeypatch.setattr("config.settings.data_raw_dir", tmp_path / "raw")
    yield
    monkeypatch.setattr("graph.store._conn", None)


def test_tool_rebuilds_from_disk_when_edges_empty(graph_env):
    from agent.tools.builtins.relationship_graph import (
        clear_relationship_graph_context,
        set_relationship_graph_context,
        show_relationship_graph,
    )
    from graph.viz import parse_graph_viz_from_tool_output

    set_relationship_graph_context(user_department="技术部", max_hops=2)
    try:
        out = show_relationship_graph(
            query="展示科技公司员工关系",
            center_name="张振国",
        )
        assert "图谱中暂无关系边" not in out
        viz = parse_graph_viz_from_tool_output(out)
        assert viz is not None
        assert len(viz["edges"]) >= 2
        assert len(viz["nodes"]) >= 3
    finally:
        clear_relationship_graph_context()
