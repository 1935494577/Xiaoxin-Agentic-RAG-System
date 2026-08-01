"""Persist retrieval tuning overrides (RRF k, legacy hybrid weights) for actuator patches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings

_ALLOWED = frozenset({"rrf_k", "hybrid_vector_weight", "hybrid_bm25_weight"})


def _path() -> Path:
    return Path(settings.retrieval_tuning_path)


def load_retrieval_tuning() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_retrieval_tuning(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_retrieval_tuning()
    for k, v in patch.items():
        if k not in _ALLOWED or v is None:
            continue
        if k == "rrf_k":
            try:
                current[k] = max(1, int(v))
            except (TypeError, ValueError):
                continue
            continue
        try:
            current[k] = float(v)
        except (TypeError, ValueError):
            continue
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def get_rrf_k() -> int:
    tuning = load_retrieval_tuning()
    raw = tuning.get("rrf_k", settings.rrf_k)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return max(1, int(settings.rrf_k or 60))
