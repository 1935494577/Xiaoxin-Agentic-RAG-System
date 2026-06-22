"""Tests for knowledge graph SQLite store."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def graph_db(tmp_path, monkeypatch):
    db = tmp_path / "test_graph.db"
    monkeypatch.setattr("graph.store.settings.graph_db_path", db)
    monkeypatch.setattr("graph.store._conn", None)
    yield db
    monkeypatch.setattr("graph.store._conn", None)


def test_upsert_and_expand(graph_db):
    from graph.store import expand_from_seeds, upsert_triple

    upsert_triple(
        src_name="产品A",
        relation="依赖",
        dst_name="组件X",
        source="test.pdf",
        department="技术部",
        parent_id="p1",
        confidence=0.9,
    )
    upsert_triple(
        src_name="组件X",
        relation="供应",
        dst_name="供应商Y",
        source="test.pdf",
        department="技术部",
        parent_id="p2",
        confidence=0.85,
    )
    edges = expand_from_seeds(["产品A"], department="技术部", max_hops=2)
    assert len(edges) >= 1
    names = {e["src_name"] for e in edges} | {e["dst_name"] for e in edges}
    assert "产品A" in names or "组件X" in names


def test_rrf_fuse():
    from graph.retrieve import rrf_fuse_parents

    hybrid = [{"parent_id": "a", "text": "A", "hybrid_score": 0.9}]
    graph = [{"parent_id": "b", "text": "B", "hybrid_score": 0.7}]
    fused = rrf_fuse_parents(hybrid, graph, top_k=2)
    assert len(fused) == 2
    ids = {r["parent_id"] for r in fused}
    assert ids == {"a", "b"}
