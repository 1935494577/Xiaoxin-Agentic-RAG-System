"""Debug session NDJSON log writer (repo-root path, stable across cwd)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

SESSION_ID = "178feb"
LOG_NAME = f"debug-{SESSION_ID}.log"


def log_path() -> Path:
    # enterprise_rag/src -> repo root
    return Path(__file__).resolve().parents[2] / LOG_NAME


def write(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any],
    *,
    run_id: str | None = None,
) -> None:
    # #region agent log
    try:
        payload: dict[str, Any] = {
            "sessionId": SESSION_ID,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        if run_id:
            payload["runId"] = run_id
        with log_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion
