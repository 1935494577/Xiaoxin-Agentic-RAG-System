"""Optional Redis cache for hybrid search results."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Protocol

from config import settings

logger = logging.getLogger(__name__)

_cached_client: Any | None = None
_cached_impl: "SearchCache | None" = None


class SearchCache(Protocol):
    def get(self, key: str) -> tuple[str, list[dict[str, Any]]] | None: ...

    def set(self, key: str, rewritten_query: str, parents: list[dict[str, Any]]) -> None: ...

    def invalidate_all(self) -> None: ...


class NullSearchCache:
    def get(self, key: str) -> tuple[str, list[dict[str, Any]]] | None:
        return None

    def set(self, key: str, rewritten_query: str, parents: list[dict[str, Any]]) -> None:
        return None

    def invalidate_all(self) -> None:
        return None


class MemorySearchCache:
    """In-process TTL cache when Redis is unavailable (dev/single-worker)."""

    def __init__(self, *, ttl_seconds: int, max_entries: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max(16, max_entries)
        self._store: OrderedDict[str, tuple[float, str, list[dict[str, Any]]]] = OrderedDict()

    def get(self, key: str) -> tuple[str, list[dict[str, Any]]] | None:
        row = self._store.get(key)
        if row is None:
            return None
        expires_at, rewritten, parents = row
        if expires_at <= time.monotonic():
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return rewritten, parents

    def set(self, key: str, rewritten_query: str, parents: list[dict[str, Any]]) -> None:
        expires_at = time.monotonic() + self.ttl_seconds
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (expires_at, rewritten_query, parents)
        while len(self._store) > self.max_entries:
            self._store.popitem(last=False)

    def invalidate_all(self) -> None:
        self._store.clear()


class RedisSearchCache:
    """Redis string cache with TTL (plugin: ram-ttl, data-key-naming, conn-pooling)."""

    def __init__(self, client: Any, *, ttl_seconds: int) -> None:
        self._client = client
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> tuple[str, list[dict[str, Any]]] | None:
        try:
            raw = self._client.get(key)
        except Exception:
            logger.warning("Redis search cache get failed", exc_info=True)
            return None
        if not raw:
            return None
        try:
            payload = json.loads(raw)
            rewritten = str(payload.get("rewritten_query") or "")
            parents = payload.get("parents")
            if not isinstance(parents, list):
                return None
            return rewritten, parents
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def set(self, key: str, rewritten_query: str, parents: list[dict[str, Any]]) -> None:
        payload = json.dumps(
            {"rewritten_query": rewritten_query, "parents": parents},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            self._client.setex(key, self.ttl_seconds, payload)
        except Exception:
            logger.warning("Redis search cache set failed", exc_info=True)

    def invalidate_all(self) -> None:
        pattern = "rag:search:v1:*"
        try:
            batch: list[str] = []
            for key in self._client.scan_iter(match=pattern, count=200):
                batch.append(key)
                if len(batch) >= 200:
                    self._client.delete(*batch)
                    batch.clear()
            if batch:
                self._client.delete(*batch)
        except Exception:
            logger.warning("Redis search cache invalidate failed", exc_info=True)


def build_search_cache_key(query: str, user_department: str, **search_params: Any) -> str:
    from security.access_control import normalize_department

    dept = normalize_department(user_department or settings.default_department)
    canonical = {
        "query": query.strip(),
        "department": dept,
        **{k: search_params[k] for k in sorted(search_params)},
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:32]
    return f"rag:search:v1:{dept}:{digest}"


def _redis_client():
    global _cached_client
    if _cached_client is not None:
        return _cached_client
    url = (settings.redis_url or "").strip()
    if not url:
        return None
    try:
        import redis
        from redis.connection import ConnectionPool
    except ImportError:
        logger.warning("redis package not installed; search cache disabled")
        return None

    pool = ConnectionPool.from_url(
        url,
        max_connections=10,
        socket_connect_timeout=5,
        socket_timeout=5,
        decode_responses=True,
    )
    _cached_client = redis.Redis(connection_pool=pool)
    return _cached_client


def get_search_cache() -> SearchCache:
    global _cached_impl
    if _cached_impl is not None:
        return _cached_impl
    if not settings.redis_search_cache_enabled:
        _cached_impl = NullSearchCache()
        return _cached_impl
    ttl = int(settings.redis_search_cache_ttl_seconds)
    url = (settings.redis_url or "").strip()
    if url:
        client = _redis_client()
        if client is not None:
            _cached_impl = RedisSearchCache(client, ttl_seconds=ttl)
            return _cached_impl
        logger.warning("Redis unavailable; falling back to in-process search cache")
    _cached_impl = MemorySearchCache(
        ttl_seconds=ttl,
        max_entries=int(getattr(settings, "memory_search_cache_max_entries", 256)),
    )
    return _cached_impl


def invalidate_search_cache() -> None:
    """Drop cached hybrid-search results after index mutations (ingest, store switch)."""
    get_search_cache().invalidate_all()
