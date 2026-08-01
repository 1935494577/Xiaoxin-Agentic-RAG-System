"""Hybrid search retrieval modes: exact / semantic / hybrid paths."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

_STUB = Path(__file__).resolve().parent / "conftest_hybrid_stubs.py"
_spec = importlib.util.spec_from_file_location("_hybrid_stubs", _STUB)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)


@pytest.fixture(scope="module", autouse=True)
def _hybrid_stub_isolation():
    prior = _mod.install_hybrid_search_stubs()
    for name in ("retrieval.hybrid_searcher", "retrieval"):
        sys.modules.pop(name, None)
    hybrid_searcher = importlib.import_module("retrieval.hybrid_searcher")
    yield hybrid_searcher
    _mod.restore_hybrid_search_stubs(prior)
    for name in ("retrieval.hybrid_searcher", "retrieval"):
        sys.modules.pop(name, None)


@pytest.fixture(autouse=True)
def _null_cache(_hybrid_stub_isolation, monkeypatch):
    from retrieval.search_cache import NullSearchCache

    hs = _hybrid_stub_isolation
    monkeypatch.setattr(hs, "get_search_cache", lambda: NullSearchCache())
    monkeypatch.setattr(hs.settings, "query_normalize_enabled", False)


def _fake_vec_hits():
    return [{"parent_id": "p-vec", "text": "语义块", "score": 0.82, "department": "general"}]


def _fake_bm25_hits():
    return [{"parent_id": "p-bm25", "text": "关键词块", "score": 12.5, "department": "general"}]


@patch("retrieval.hybrid_searcher.rerank_parents", side_effect=lambda q, items, top_k=None: items)
@patch("retrieval.hybrid_searcher.bm25_parent_search", return_value=_fake_bm25_hits())
@patch("retrieval.hybrid_searcher.vector_search", return_value=_fake_vec_hits())
@patch("retrieval.hybrid_searcher.embed_texts")
def test_exact_mode_skips_embedding(embed_mock, _vec, bm25_mock, _rerank, _hybrid_stub_isolation):
    hs = _hybrid_stub_isolation
    meta: dict = {}
    _, parents = hs.hybrid_search(
        "WO-8827391",
        "general",
        top_k=3,
        skip_query_rewrite=True,
        skip_rerank=True,
        retrieval_mode="exact",
        retrieval_meta_out=meta,
    )
    embed_mock.assert_not_called()
    bm25_mock.assert_called_once()
    assert meta.get("retrieval_mode") == "exact"
    assert meta.get("paths_used") == ["bm25"]
    assert parents and parents[0]["parent_id"] == "p-bm25"


@patch("retrieval.hybrid_searcher.rerank_parents", side_effect=lambda q, items, top_k=None: items)
@patch("retrieval.hybrid_searcher.bm25_parent_search", return_value=_fake_bm25_hits())
@patch("retrieval.hybrid_searcher.vector_search", return_value=_fake_vec_hits())
@patch("retrieval.hybrid_searcher.embed_texts")
def test_semantic_mode_skips_bm25(embed_mock, vec_mock, bm25_mock, _rerank, _hybrid_stub_isolation):
    hs = _hybrid_stub_isolation
    embed_mock.side_effect = lambda texts: [np.zeros(8) for _ in texts]
    meta: dict = {}
    _, parents = hs.hybrid_search(
        "怎么报销差旅费",
        "general",
        top_k=3,
        skip_query_rewrite=True,
        skip_rerank=True,
        retrieval_mode="semantic",
        retrieval_meta_out=meta,
    )
    bm25_mock.assert_not_called()
    vec_mock.assert_called_once()
    assert meta.get("retrieval_mode") == "semantic"
    assert meta.get("paths_used") == ["vector"]
    assert parents[0]["parent_id"] == "p-vec"


@patch("retrieval.hybrid_searcher.rerank_parents", side_effect=lambda q, items, top_k=None: items)
@patch("retrieval.hybrid_searcher.bm25_parent_search", return_value=_fake_bm25_hits())
@patch("retrieval.hybrid_searcher.vector_search", return_value=_fake_vec_hits())
@patch("retrieval.hybrid_searcher.embed_texts")
def test_hybrid_mode_uses_both_paths(embed_mock, vec_mock, bm25_mock, _rerank, _hybrid_stub_isolation):
    hs = _hybrid_stub_isolation
    embed_mock.side_effect = lambda texts: [np.zeros(8) for _ in texts]
    meta: dict = {}
    hs.hybrid_search(
        "2024浙江高三数学函数",
        "general",
        top_k=3,
        skip_query_rewrite=True,
        skip_rerank=True,
        retrieval_mode="hybrid",
        retrieval_meta_out=meta,
    )
    bm25_mock.assert_called_once()
    vec_mock.assert_called_once()
    assert set(meta.get("paths_used") or []) == {"bm25", "vector", "rrf"}


@patch("retrieval.hybrid_searcher._rrf_fuse")
@patch("retrieval.hybrid_searcher.rerank_parents", side_effect=lambda q, items, top_k=None: items)
@patch("retrieval.hybrid_searcher.bm25_parent_search", return_value=_fake_bm25_hits())
@patch("retrieval.hybrid_searcher.vector_search", return_value=_fake_vec_hits())
@patch("retrieval.hybrid_searcher.embed_texts")
def test_hybrid_single_variant_calls_rrf(
    embed_mock, _vec, _bm25, _rerank, rrf_mock, _hybrid_stub_isolation
):
    hs = _hybrid_stub_isolation
    embed_mock.side_effect = lambda texts: [np.zeros(8) for _ in texts]
    rrf_mock.return_value = {"p-bm25": 0.03, "p-vec": 0.02}
    hs.hybrid_search(
        "浙江高三数学",
        "general",
        top_k=3,
        skip_query_rewrite=True,
        skip_rerank=True,
        retrieval_mode="hybrid",
    )
    rrf_mock.assert_called_once()
