"""Windows：无 milvus-lite 轮子时用纯 NumPy 做子块向量检索（plan1 无 Docker）。"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import numpy as np

from config import settings

_lock = threading.Lock()
_rows: list[dict[str, Any]] = []


def _path() -> Path:
    return Path(settings.numpy_vector_store_path)


def _load_unlocked() -> None:
    global _rows
    p = _path()
    if not p.is_file():
        _rows = []
        return
    with p.open(encoding="utf-8") as f:
        _rows = json.load(f)


def _save_unlocked() -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(_rows, f, ensure_ascii=False)


def init_store() -> None:
    with _lock:
        _load_unlocked()


def delete_by_source(source: str) -> None:
    global _rows
    with _lock:
        _load_unlocked()
        _rows = [r for r in _rows if str(r.get("source", "")) != source]
        _save_unlocked()


def insert_child_vectors(
    ids: list[str],
    vectors: list[list[float]],
    texts: list[str],
    parent_ids: list[str],
    departments: list[str],
    sources: list[str],
) -> None:
    with _lock:
        _load_unlocked()
        for i in range(len(ids)):
            _rows.append(
                {
                    "id": ids[i],
                    "vector": vectors[i],
                    "text": texts[i][:1990],
                    "parent_id": parent_ids[i],
                    "department": departments[i],
                    "source": sources[i],
                }
            )
        _save_unlocked()


def vector_search(
    query_vector: list[float],
    top_k: int,
    user_department: str | None = None,
) -> list[dict[str, Any]]:
    q = np.asarray(query_vector, dtype=np.float32)
    qn = np.linalg.norm(q) + 1e-12
    q = q / qn
    with _lock:
        _load_unlocked()
        scored: list[tuple[float, dict[str, Any]]] = []
        for r in _rows:
            if user_department and str(r.get("department", "")) != user_department:
                continue
            v = np.asarray(r["vector"], dtype=np.float32)
            vn = np.linalg.norm(v) + 1e-12
            v = v / vn
            sim = float(np.dot(q, v))
            scored.append((sim, r))
        scored.sort(key=lambda x: -x[0])
        out: list[dict[str, Any]] = []
        for sim, r in scored[:top_k]:
            out.append(
                {
                    "id": r.get("id"),
                    "parent_id": r.get("parent_id"),
                    "department": r.get("department"),
                    "source": r.get("source"),
                    "text": r.get("text"),
                    "score": sim,
                }
            )
        return out
