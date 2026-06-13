"""Shared golden.jsonl loading and metric scoring for offline + feedback evaluate."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from config import settings
from evaluation.ragas_scorer import _load_golden, _naive_metrics, score_rag_batch


def golden_path() -> Path:
    return Path(settings.golden_jsonl_path)


def load_golden_rows(path: Path | None = None) -> dict[str, list]:
    p = path or golden_path()
    if not p.is_file():
        return {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    return _load_golden(p)


def _sanitize_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if hasattr(v, "item") and not isinstance(v, (bytes, str)):
            try:
                out[str(k)] = float(v)  # type: ignore[arg-type]
                continue
            except Exception:
                pass
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[str(k)] = None
        elif isinstance(v, (int, float, str, bool)) or v is None:
            out[str(k)] = v
        else:
            out[str(k)] = str(v)
    return out


def run_golden_metrics(rows: dict[str, list]) -> dict[str, Any]:
    """RAGAS when API key present; otherwise naive overlap metrics."""
    if not rows.get("question"):
        return {"mode": "empty", "rows": 0.0}
    if not (settings.openai_api_key or "").strip():
        metrics = _naive_metrics(rows)
        metrics["mode"] = "fallback_naive"
        return _sanitize_metrics(metrics)
    try:
        metrics = score_rag_batch(rows)
        metrics["mode"] = "ragas"
        return _sanitize_metrics(metrics)
    except Exception as e:
        metrics = _naive_metrics(rows)
        metrics["mode"] = "fallback_naive"
        metrics["ragas_error"] = str(e)[:500]
        return _sanitize_metrics(metrics)
