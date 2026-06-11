"""Hybrid search Redis cache tests (TDD)."""

from __future__ import annotations

import json

import pytest

from retrieval.search_cache import (
    NullSearchCache,
    RedisSearchCache,
    build_search_cache_key,
    get_search_cache,
)


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value
        self._ttl[key] = ttl


def test_build_search_cache_key_is_stable_and_namespaced():
    k1 = build_search_cache_key("请假流程", "hr", retrieve_top_k=20, rerank_top_k=5)
    k2 = build_search_cache_key("请假流程", "hr", retrieve_top_k=20, rerank_top_k=5)
    k3 = build_search_cache_key("请假流程", "finance", retrieve_top_k=20, rerank_top_k=5)

    assert k1 == k2
    assert k1.startswith("rag:search:v1:hr:")
    assert k3.startswith("rag:search:v1:finance:")
    assert k1 != k3


def test_redis_search_cache_roundtrip():
    fake = _FakeRedis()
    cache = RedisSearchCache(fake, ttl_seconds=300)
    key = build_search_cache_key("q", "general")
    parents = [{"parent_id": "p1", "text": "制度 A", "hybrid_score": 0.9}]

    assert cache.get(key) is None
    cache.set(key, "rewritten q", parents)
    hit = cache.get(key)
    assert hit is not None
    rewritten, got = hit
    assert rewritten == "rewritten q"
    assert got[0]["parent_id"] == "p1"
    assert fake._ttl[key] == 300


def test_redis_search_cache_handles_corrupt_payload():
    fake = _FakeRedis()
    cache = RedisSearchCache(fake, ttl_seconds=60)
    key = "rag:search:v1:general:deadbeef"
    fake.setex(key, 60, "not-json")
    assert cache.get(key) is None


def test_null_search_cache_is_noop():
    cache = NullSearchCache()
    key = build_search_cache_key("x", "general")
    cache.set(key, "r", [{"parent_id": "p"}])
    assert cache.get(key) is None


def test_get_search_cache_returns_null_without_url(monkeypatch):
    monkeypatch.setattr("retrieval.search_cache._cached_client", None)
    monkeypatch.setattr("retrieval.search_cache._cached_impl", None)
    from config import settings

    monkeypatch.setattr(settings, "redis_url", "")
    monkeypatch.setattr(settings, "redis_search_cache_enabled", True)
    assert isinstance(get_search_cache(), NullSearchCache)


def test_get_search_cache_uses_redis_when_configured(monkeypatch):
    monkeypatch.setattr("retrieval.search_cache._cached_client", None)
    monkeypatch.setattr("retrieval.search_cache._cached_impl", None)
    from config import settings

    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:6379/0")
    monkeypatch.setattr(settings, "redis_search_cache_enabled", True)
    monkeypatch.setattr(settings, "redis_search_cache_ttl_seconds", 120)

    class _Pool:
        @staticmethod
        def from_url(*_a, **_k):
            return object()

    class _Redis:
        def __init__(self, **_k):
            pass

    monkeypatch.setattr("redis.connection.ConnectionPool", _Pool)
    monkeypatch.setattr("redis.Redis", _Redis)

    impl = get_search_cache()
    assert isinstance(impl, RedisSearchCache)
    assert impl.ttl_seconds == 120
