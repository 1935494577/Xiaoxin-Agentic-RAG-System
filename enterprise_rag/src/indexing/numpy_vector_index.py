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
_loaded_path: str | None = None


def _path() -> Path:
    try:
        from api.vector_store_registry import get_active_numpy_path

        return get_active_numpy_path()
    except Exception:
        return Path(settings.numpy_vector_store_path)


def reload_store() -> None:
    global _loaded_path
    with _lock:
        _loaded_path = None
        _load_unlocked()


def _load_unlocked() -> None:
    global _rows, _loaded_path
    p = _path()
    key = str(p.resolve())
    if _loaded_path == key and _rows is not None:
        return
    _loaded_path = key
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


def vector_count_and_dim() -> tuple[int, int | None]:
    with _lock:
        _load_unlocked()
        if not _rows:
            return 0, None
        dim = len(_rows[0].get("vector") or [])
        return len(_rows), dim or None


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
    tags: list[str] | None = None,
) -> None:
    try:
        from api.vector_store_registry import validate_insert_vectors

        validate_insert_vectors(vectors)
    except ImportError:
        pass
    from chunker.utils import tags_to_store_value

    tag_str = tags_to_store_value(tags)
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
                    "tags": tag_str,
                }
            )
        _save_unlocked()


def vector_search(
    query_vector: list[float],
    top_k: int,
    user_department: str | None = None,
) -> list[dict[str, Any]]:
    q = np.asarray(query_vector, dtype=np.float32)
    try:
        from api.vector_store_registry import assert_search_compatible

        assert_search_compatible(int(q.shape[0]))
    except ImportError:
        pass
    qn = np.linalg.norm(q) + 1e-12
    q = q / qn
    with _lock:
        _load_unlocked()
        if _rows:
            stored_dim = len(_rows[0].get("vector") or [])
            if stored_dim and stored_dim != q.shape[0]:
                raise ValueError(
                    f"向量维度不一致：当前查询模型输出 {q.shape[0]} 维，"
                    f"索引中为 {stored_dim} 维。"
                    "请用同一嵌入模型重新入库（数据入库页重新上传），或清空向量库后重建索引。"
                )
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
                    "tags": r.get("tags") or "",
                    "score": sim,
                }
            )
        return out
