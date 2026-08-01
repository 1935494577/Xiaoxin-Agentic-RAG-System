"""Hybrid search Redis cache integration."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

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


class _RecordingCache:
    def __init__(self) -> None:
        self.store: dict[str, tuple[str, list]] = {}
        self.get_calls = 0
        self.set_calls = 0

    def get(self, key: str):
        self.get_calls += 1
        return self.store.get(key)

    def set(self, key: str, rewritten_query: str, parents: list) -> None:
        self.set_calls += 1
        self.store[key] = (rewritten_query, parents)

    def invalidate_all(self) -> None:
        self.store.clear()


@pytest.fixture()
def recording_cache(_hybrid_stub_isolation, monkeypatch):
    from retrieval.search_cache import NullSearchCache

    cache = _RecordingCache()
    monkeypatch.setattr(_hybrid_stub_isolation, "get_search_cache", lambda: cache)
    return cache


def test_hybrid_search_returns_cached_result_without_retrieval(recording_cache, _hybrid_stub_isolation):
    from retrieval.search_cache import build_search_cache_key

    hs = _hybrid_stub_isolation
    query = "年假怎么请"
    dept = "hr"
    key = build_search_cache_key(
        query,
        dept,
        top_k=5,
        skip_query_rewrite=True,
        retrieve_top_k=20,
        skip_rerank=True,
        rerank_top_k=5,
        pre_rerank_k=None,
        retrieval_dedup=True,
        query_rewrite_enabled=False,
        query_normalize_enabled=True,
        retrieval_mode="semantic",
    )
    parents = [{"parent_id": "p1", "text": "年假制度", "hybrid_score": 0.95}]
    recording_cache.store[key] = ("年假 申请", parents)

    with patch.object(hs, "embed_texts") as embed_mock:
        rewritten, got = hs.hybrid_search(
            query,
            dept,
            top_k=5,
            skip_query_rewrite=True,
            retrieve_top_k=20,
            skip_rerank=True,
            rerank_top_k=5,
            retrieval_dedup=True,
            retrieval_mode="semantic",
        )

    embed_mock.assert_not_called()
    assert recording_cache.get_calls == 1
    assert recording_cache.set_calls == 0
    assert rewritten == "年假 申请"
    assert got[0]["parent_id"] == "p1"
