"""Versioned config changes produced by feedback actuator."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from config import settings

_lock = Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path() -> Path:
    return Path(settings.config_revisions_path)


def _read_all() -> list[dict[str, Any]]:
    path = _path()
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except OSError:
        return []
    return rows


def _write_all(rows: list[dict[str, Any]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_revision(
    *,
    feedback_id: str,
    action: str,
    before: dict[str, Any],
    after: dict[str, Any],
    patch: dict[str, Any],
    tenant_id: str = "internal",
) -> dict[str, Any]:
    row = {
        "id": uuid.uuid4().hex,
        "created_at": _utc_now(),
        "feedback_id": feedback_id,
        "tenant_id": tenant_id,
        "action": action,
        "before": before,
        "after": after,
        "patch": patch,
        "rolled_back": False,
        "rolled_back_at": None,
    }
    with _lock:
        rows = _read_all()
        rows.append(row)
        _write_all(rows)
    return row


def list_revisions(
    *,
    tenant_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    rows = _read_all()
    if tenant_id:
        rows = [r for r in rows if str(r.get("tenant_id") or "internal") == tenant_id]
    rows = sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)
    total = len(rows)
    off = max(0, int(offset))
    lim = max(1, min(int(limit), 100))
    return rows[off : off + lim], total


def get_revision(revision_id: str) -> dict[str, Any] | None:
    rid = revision_id.strip()
    if not rid:
        return None
    for row in _read_all():
        if str(row.get("id") or "") == rid:
            return row
    return None


def diff_revision(revision: dict[str, Any]) -> dict[str, Any]:
    before = revision.get("before") if isinstance(revision.get("before"), dict) else {}
    after = revision.get("after") if isinstance(revision.get("after"), dict) else {}
    keys = sorted(set(before) | set(after))
    changes: dict[str, dict[str, Any]] = {}
    for k in keys:
        b = before.get(k)
        a = after.get(k)
        if b != a:
            changes[k] = {"before": b, "after": a}
    return changes


def rollback_revision(revision_id: str) -> dict[str, Any]:
    rid = revision_id.strip()
    if not rid:
        raise KeyError("revision not found")
    with _lock:
        rows = _read_all()
        target: dict[str, Any] | None = None
        for row in rows:
            if str(row.get("id") or "") == rid:
                target = row
                break
        if not target:
            raise KeyError("revision not found")
        if target.get("rolled_back"):
            return target
        from feedback_loop.actuator import restore_config_snapshot

        before = target.get("before")
        if not isinstance(before, dict):
            raise ValueError("invalid revision snapshot")
        restore_config_snapshot(before)
        target["rolled_back"] = True
        target["rolled_back_at"] = _utc_now()
        _write_all(rows)
        return target
