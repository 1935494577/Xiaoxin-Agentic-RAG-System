"""Hybrid search Redis cache integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from retrieval import hybrid_searcher
from retrieval.search_cache import NullSearchCache, build_search_cache_key


class _RecordingCache(NullSearchCache):
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


@pytest.fixture()
def recording_cache(monkeypatch):
    cache = _RecordingCache()
    monkeypatch.setattr(hybrid_searcher, "get_search_cache", lambda: cache)
    return cache


def test_hybrid_search_returns_cached_result_without_retrieval(recording_cache):
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
    )
    parents = [{"parent_id": "p1", "text": "年假制度", "hybrid_score": 0.95}]
    recording_cache.store[key] = ("年假 申请", parents)

    with patch.object(hybrid_searcher, "embed_texts") as embed_mock:
        rewritten, got = hybrid_searcher.hybrid_search(
            query,
            dept,
            skip_query_rewrite=True,
            skip_rerank=True,
        )

    embed_mock.assert_not_called()
    assert recording_cache.get_calls == 1
    assert recording_cache.set_calls == 0
    assert rewritten == "年假 申请"
    assert got[0]["parent_id"] == "p1"
