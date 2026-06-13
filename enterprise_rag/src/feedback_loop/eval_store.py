"""Persist golden evaluation reports (JSONL)."""

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
    return Path(settings.eval_reports_path)


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


def append_eval_report(
    *,
    metrics: dict[str, Any],
    golden_rows: int,
    feedback_id: str | None = None,
    revision_id: str | None = None,
    baseline_metrics: dict[str, Any] | None = None,
    delta: dict[str, Any] | None = None,
    mode: str = "fallback_naive",
) -> dict[str, Any]:
    row = {
        "id": uuid.uuid4().hex,
        "created_at": _utc_now(),
        "feedback_id": feedback_id,
        "revision_id": revision_id,
        "golden_rows": int(golden_rows),
        "mode": mode,
        "metrics": metrics,
        "baseline_metrics": baseline_metrics or {},
        "delta": delta or {},
    }
    with _lock:
        rows = _read_all()
        rows.append(row)
        _write_all(rows)
    return row


def list_eval_reports(
    *,
    feedback_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    rows = _read_all()
    if feedback_id:
        fid = feedback_id.strip()
        rows = [r for r in rows if str(r.get("feedback_id") or "") == fid]
    rows = sorted(rows, key=lambda r: str(r.get("created_at") or ""), reverse=True)
    total = len(rows)
    off = max(0, int(offset))
    lim = max(1, min(int(limit), 100))
    return rows[off : off + lim], total


def get_eval_report(report_id: str) -> dict[str, Any] | None:
    rid = report_id.strip()
    if not rid:
        return None
    for row in _read_all():
        if str(row.get("id") or "") == rid:
            return row
    return None


def get_latest_report(*, feedback_id: str | None = None) -> dict[str, Any] | None:
    items, _ = list_eval_reports(feedback_id=feedback_id, limit=1)
    return items[0] if items else None


def export_reports_json() -> list[dict[str, Any]]:
    return _read_all()
