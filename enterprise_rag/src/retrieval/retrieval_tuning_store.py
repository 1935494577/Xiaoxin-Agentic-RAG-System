"""Persist retrieval tuning overrides (hybrid weights) for actuator patches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings

_ALLOWED = frozenset({"hybrid_vector_weight", "hybrid_bm25_weight"})


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
        try:
            current[k] = float(v)
        except (TypeError, ValueError):
            continue
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def get_hybrid_weights() -> tuple[float, float]:
    tuning = load_retrieval_tuning()
    wv = tuning.get("hybrid_vector_weight", settings.hybrid_vector_weight)
    wb = tuning.get("hybrid_bm25_weight", settings.hybrid_bm25_weight)
    try:
        wv_f = float(wv)
        wb_f = float(wb)
    except (TypeError, ValueError):
        return settings.hybrid_vector_weight, settings.hybrid_bm25_weight
    total = wv_f + wb_f
    if total <= 0:
        return settings.hybrid_vector_weight, settings.hybrid_bm25_weight
    return wv_f / total, wb_f / total
