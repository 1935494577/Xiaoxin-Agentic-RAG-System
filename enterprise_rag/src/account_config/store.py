"""Platform baseline + per-user config overrides with versioned cache."""

from __future__ import annotations

import json
import sqlite3
import time
from copy import deepcopy
from threading import Lock
from typing import Any, Callable

from config import settings

_lock = Lock()
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 30


def _db_path():
    return settings.platform_config_db_path


def init_platform_config_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS platform_meta (
                    scope TEXT PRIMARY KEY,
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL DEFAULT '',
                    updated_by TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS user_config (
                    user_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (user_id, scope)
                );
                """
            )
            conn.commit()
        finally:
            conn.close()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def get_platform_version(scope: str) -> int:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT version FROM platform_meta WHERE scope = ?",
                (scope,),
            ).fetchone()
            return int(row["version"]) if row else 1
        finally:
            conn.close()


def bump_platform_version(scope: str, *, updated_by: str = "") -> int:
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT version FROM platform_meta WHERE scope = ?",
                (scope,),
            ).fetchone()
            version = int(row["version"]) + 1 if row else 1
            conn.execute(
                """
                INSERT INTO platform_meta (scope, version, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scope) DO UPDATE SET
                    version = excluded.version,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """,
                (scope, version, now, updated_by or ""),
            )
            conn.commit()
            _invalidate_scope_cache(scope)
            return version
        finally:
            conn.close()


def _cache_key(scope: str, user_id: str | None, version: int) -> str:
    return f"{scope}:{user_id or '_anon_'}:v{version}"


def _invalidate_scope_cache(scope: str) -> None:
    prefix = f"{scope}:"
    for key in list(_CACHE):
        if key.startswith(prefix):
            del _CACHE[key]


def get_user_override(user_id: str, scope: str) -> dict[str, Any] | None:
    uid = (user_id or "").strip()
    if not uid:
        return None
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT payload FROM user_config WHERE user_id = ? AND scope = ?",
                (uid, scope),
            ).fetchone()
            if not row:
                return None
            data = json.loads(str(row["payload"]))
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None
        finally:
            conn.close()


def set_user_override(user_id: str, scope: str, payload: dict[str, Any]) -> None:
    uid = (user_id or "").strip()
    if not uid:
        raise ValueError("user_id required")
    now = _utc_now()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO user_config (user_id, scope, payload, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, scope) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (uid, scope, json.dumps(payload, ensure_ascii=False), now),
            )
            conn.commit()
        finally:
            conn.close()
    _invalidate_scope_cache(scope)


def save_user_scope_patch(user_id: str, scope: str, patch: dict[str, Any]) -> dict[str, Any]:
    current = get_user_override(user_id, scope) or {}
    merged = deep_merge(current, patch)
    set_user_override(user_id, scope, merged)
    return merged


def save_platform_scope(scope: str, *, updated_by: str = "") -> int:
    return bump_platform_version(scope, updated_by=updated_by)


def effective_json_config(
    scope: str,
    baseline_loader: Callable[[], dict[str, Any]],
    *,
    user_id: str | None,
) -> dict[str, Any]:
    version = get_platform_version(scope)
    key = _cache_key(scope, user_id or "_anon_", version)
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return deepcopy(cached[1])

    baseline = baseline_loader()
    if user_id:
        override = get_user_override(user_id, scope)
        result = deep_merge(baseline, override) if override else baseline
    else:
        result = baseline

    _CACHE[key] = (now, deepcopy(result))
    return result


def effective_ui_config(user_id: str | None) -> dict[str, Any]:
    from api.ui_config_store import public_ui_config

    return effective_json_config("ui", public_ui_config, user_id=user_id)


def effective_prompt_bundle(
    user_id: str | None,
    *,
    mode: str = "kb",
    fast: bool = False,
) -> dict[str, Any]:
    from agent.prompt_engine import compose_system_prompt, preview_layers
    from api.prompt_config_store import _merge_builtin_defaults, load_prompt_slots, public_prompt_config

    scope = f"prompts:{mode}:{'fast' if fast else 'std'}"
    base = public_prompt_config(mode=mode, fast=fast)
    override = get_user_override(user_id, scope) if user_id else None
    if not override:
        return base

    slots = base.get("slots")
    if override.get("slots"):
        slots = _merge_builtin_defaults(override["slots"])
    elif slots is None:
        slots = load_prompt_slots()

    m = mode if mode in ("kb", "general") else "kb"
    reasoning_mode = override.get("agent_reasoning_mode") or base.get("agent_reasoning_mode")
    out = dict(base)
    out["agent_reasoning_mode"] = reasoning_mode
    if override.get("active_persona_id"):
        out["active_persona_id"] = override["active_persona_id"]
    out["preview"] = {
        "mode": m,
        "fast": fast,
        "layers": preview_layers(slots, mode=m, fast=fast),  # type: ignore[arg-type]
        "composed": compose_system_prompt(slots, mode=m, fast=fast),  # type: ignore[arg-type]
    }
    return out


def effective_prompt_slots_list(user_id: str | None) -> list[dict[str, Any]]:
    from api.prompt_config_store import _merge_builtin_defaults, load_prompt_slots

    if not user_id:
        return load_prompt_slots()
    override = get_user_override(user_id, "prompts:kb:std") or {}
    if override.get("slots"):
        return _merge_builtin_defaults(override["slots"])
    return load_prompt_slots()


def effective_processing_tools(user_id: str | None) -> dict[str, Any]:
    from document_loader.processing.registry import load_config, public_config

    return effective_json_config(
        "processing_tools",
        lambda: public_config(load_config()),
        user_id=user_id,
    )


def effective_agent_tools(user_id: str | None) -> dict[str, Any]:
    from agent.tools.config.registry import load_tools_config, public_tools_config

    return effective_json_config(
        "agent_tools",
        lambda: public_tools_config(load_tools_config()),
        user_id=user_id,
    )


def list_user_config_scopes(user_id: str) -> list[str]:
    uid = (user_id or "").strip()
    if not uid:
        return []
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT scope FROM user_config WHERE user_id = ? ORDER BY scope",
                (uid,),
            ).fetchall()
            return [str(r["scope"]) for r in rows]
        finally:
            conn.close()
