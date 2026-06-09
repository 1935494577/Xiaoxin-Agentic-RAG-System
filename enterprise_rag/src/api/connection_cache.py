"""TTL cache for LLM connectivity probes (avoid blocking every page load)."""

from __future__ import annotations

import time
from threading import Lock

_lock = Lock()
_store: dict[str, tuple[float, bool, str]] = {}
DEFAULT_TTL_SEC = 120.0


def _cache_key(profile_id: str | None, force_env: bool) -> str:
    return f"{force_env}|{profile_id or ''}"


def get_cached_status(
    profile_id: str | None,
    force_env: bool,
    *,
    ttl_sec: float = DEFAULT_TTL_SEC,
) -> tuple[bool, str] | None:
    key = _cache_key(profile_id, force_env)
    now = time.monotonic()
    with _lock:
        row = _store.get(key)
        if not row:
            return None
        ts, ok, msg = row
        if now - ts > ttl_sec:
            return None
        return ok, msg


def set_cached_status(profile_id: str | None, force_env: bool, ok: bool, msg: str) -> None:
    key = _cache_key(profile_id, force_env)
    with _lock:
        _store[key] = (time.monotonic(), ok, msg)


def invalidate_status(profile_id: str | None = None, force_env: bool | None = None) -> None:
    with _lock:
        if profile_id is None and force_env is None:
            _store.clear()
            return
        keys = list(_store.keys())
        for key in keys:
            parts = key.split("|", 1)
            fe = parts[0] == "True"
            pid = parts[1] if len(parts) > 1 else ""
            if force_env is not None and fe != force_env:
                continue
            if profile_id is not None and pid != profile_id:
                continue
            _store.pop(key, None)
