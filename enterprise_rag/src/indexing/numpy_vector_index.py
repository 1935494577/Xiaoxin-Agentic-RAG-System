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
_matrix: np.ndarray | None = None
_meta: list[dict[str, Any]] = []
_acl_row_cache: dict[str, np.ndarray] = {}


def _path() -> Path:
    try:
        from api.vector_store_registry import get_active_numpy_path

        return get_active_numpy_path()
    except Exception:
        return Path(settings.numpy_vector_store_path)


def _invalidate_matrix() -> None:
    global _matrix, _meta, _acl_row_cache
    _matrix = None
    _meta = []
    _acl_row_cache = {}


def reload_store() -> None:
    global _loaded_path
    with _lock:
        _loaded_path = None
        _invalidate_matrix()
        _load_unlocked()


def _load_unlocked() -> None:
    global _rows, _loaded_path
    p = _path()
    key = str(p.resolve())
    if _loaded_path == key and _rows is not None:
        return
    _loaded_path = key
    _invalidate_matrix()
    if not p.is_file():
        _rows = []
        return
    with p.open(encoding="utf-8") as f:
        _rows = json.load(f)


def _ensure_matrix_unlocked() -> None:
    global _matrix, _meta
    if _matrix is not None:
        return
    if not _rows:
        _matrix = np.zeros((0, 0), dtype=np.float32)
        _meta = []
        return
    _meta = list(_rows)
    mat = np.asarray([r["vector"] for r in _rows], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
    _matrix = mat / norms


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
        _invalidate_matrix()
        _save_unlocked()


def insert_child_vectors(
    ids: list[str],
    vectors: list[list[float]],
    texts: list[str],
    parent_ids: list[str],
    departments: list[str],
    sources: list[str],
    tags: list[str] | None = None,
    permission_labels: list[str] | None = None,
) -> None:
    try:
        from api.vector_store_registry import validate_insert_vectors

        validate_insert_vectors(vectors)
    except ImportError:
        pass
    from chunker.utils import tags_to_store_value

    tag_str = tags_to_store_value(tags)
    perms = permission_labels or ["internal"] * len(ids)
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
                    "permission_label": perms[i] if i < len(perms) else "internal",
                    "source": sources[i],
                    "tags": tag_str,
                }
            )
        _invalidate_matrix()
        _save_unlocked()


def _accessible_row_indices(user_department: str) -> np.ndarray:
    from security.access_control import can_access_row, normalize_department

    dept_key = normalize_department(user_department)
    cached = _acl_row_cache.get(dept_key)
    if cached is not None:
        return cached
    indices = [i for i, row in enumerate(_meta) if can_access_row(row, dept_key)]
    arr = np.asarray(indices, dtype=np.int32)
    _acl_row_cache[dept_key] = arr
    return arr


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
        _ensure_matrix_unlocked()
        if _matrix is None or _matrix.size == 0:
            return []
        stored_dim = int(_matrix.shape[1]) if _matrix.ndim == 2 and _matrix.shape[0] else 0
        if stored_dim and stored_dim != q.shape[0]:
            raise ValueError(
                f"向量维度不一致：当前查询模型输出 {q.shape[0]} 维，"
                f"索引中为 {stored_dim} 维。"
                "请用同一嵌入模型重新入库（数据入库页重新上传），或清空向量库后重建索引。"
            )
        if user_department:
            row_idx = _accessible_row_indices(user_department)
            if row_idx.size == 0:
                return []
            mat = _matrix[row_idx]
            meta_slice = [_meta[int(i)] for i in row_idx]
        else:
            mat = _matrix
            meta_slice = _meta
        if mat.size == 0:
            return []
        sims = mat @ q
        k = min(top_k, len(sims))
        if k <= 0:
            return []
        if k >= len(sims):
            order = np.argsort(-sims)
        else:
            part = np.argpartition(-sims, k - 1)[:k]
            order = part[np.argsort(-sims[part])]
        out: list[dict[str, Any]] = []
        for idx in order[:k]:
            r = meta_slice[int(idx)]
            out.append(
                {
                    "id": r.get("id"),
                    "parent_id": r.get("parent_id"),
                    "department": r.get("department"),
                    "permission_label": r.get("permission_label") or "",
                    "source": r.get("source"),
                    "text": r.get("text"),
                    "tags": r.get("tags") or "",
                    "score": float(sims[idx]),
                }
            )
        return out
