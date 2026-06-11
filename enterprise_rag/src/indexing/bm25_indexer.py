"""plan1：纯 Python BM25 父块索引（替代 Elasticsearch）。"""

from __future__ import annotations

import heapq
import json
import threading
from pathlib import Path
from typing import Any

import jieba
from rank_bm25 import BM25Okapi

from config import settings

_lock = threading.Lock()


def _tokenize(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    return list(jieba.cut(text))


class BM25Index:
    def __init__(self, index_path: Path | None = None) -> None:
        self.index_path = Path(index_path or settings.bm25_index_path)
        self.corpus: list[str] = []
        self.metadata_list: list[dict[str, Any]] = []
        self.bm25: BM25Okapi | None = None
        self._parent_by_id: dict[str, dict[str, Any]] | None = None
        self._acl_row_cache: dict[str, list[int]] = {}
        if self.index_path.is_file():
            self.load()

    def _invalidate_acl_cache(self) -> None:
        self._acl_row_cache = {}

    def _accessible_row_indices(self, user_department: str) -> list[int]:
        from security.access_control import can_access_row, normalize_department

        dept_key = normalize_department(user_department)
        cached = self._acl_row_cache.get(dept_key)
        if cached is not None:
            return cached
        indices = [
            i for i, meta in enumerate(self.metadata_list) if can_access_row(meta, dept_key)
        ]
        self._acl_row_cache[dept_key] = indices
        return indices

    def load(self) -> None:
        with self.index_path.open(encoding="utf-8") as f:
            data = json.load(f)
        self.corpus = list(data.get("corpus") or [])
        self.metadata_list = list(data.get("metadata_list") or [])
        self._invalidate_acl_cache()
        self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        self._parent_by_id = None
        self._invalidate_acl_cache()
        if not self.corpus:
            self.bm25 = None
            return
        tokenized = [_tokenize(t) for t in self.corpus]
        self.bm25 = BM25Okapi(tokenized)

    def _rebuild_parent_index(self) -> None:
        out: dict[str, dict[str, Any]] = {}
        for text, meta in zip(self.corpus, self.metadata_list):
            pid = str(meta.get("parent_id", ""))
            if not pid:
                continue
            out[pid] = {
                "parent_id": pid,
                "text": text,
                "department": meta.get("department"),
                "source": meta.get("source"),
                "permission_label": meta.get("permission_label"),
                "tags": meta.get("tags") or [],
            }
        self._parent_by_id = out

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"corpus": self.corpus, "metadata_list": self.metadata_list}
        with self.index_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

    def delete_by_source(self, source: str) -> None:
        with _lock:
            if not self.corpus:
                return
            new_corpus: list[str] = []
            new_meta: list[dict[str, Any]] = []
            for text, meta in zip(self.corpus, self.metadata_list):
                if str(meta.get("source", "")) == source:
                    continue
                new_corpus.append(text)
                new_meta.append(meta)
            self.corpus = new_corpus
            self.metadata_list = new_meta
            self._rebuild_bm25()
            self.save()

    def index_parent_documents(self, docs: list[dict[str, Any]]) -> int:
        """docs: parent_id, content, department, source, permission_label, tags"""
        with _lock:
            for d in docs:
                self.corpus.append(str(d.get("content") or ""))
                tags = d.get("tags") or []
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
                self.metadata_list.append(
                    {
                        "parent_id": str(d.get("parent_id", "")),
                        "department": str(d.get("department", "")),
                        "source": str(d.get("source", "")),
                        "permission_label": str(d.get("permission_label", "public")),
                        "tags": list(tags),
                    }
                )
            self._rebuild_bm25()
            self.save()
        return len(docs)

    def search(
        self,
        query: str,
        top_k: int = 20,
        user_department: str | None = None,
    ) -> list[dict[str, Any]]:
        with _lock:
            if not self.bm25 or not self.corpus:
                return []
            q_tok = _tokenize(query)
            scores = self.bm25.get_scores(q_tok)
            if user_department:
                candidate_indices = self._accessible_row_indices(user_department)
            else:
                candidate_indices = list(range(len(scores)))
            if not candidate_indices:
                return []
            k = min(top_k, len(candidate_indices))
            top_indices = heapq.nlargest(
                k, candidate_indices, key=lambda i: scores[i]
            )
            out: list[dict[str, Any]] = []
            for idx in top_indices:
                meta = self.metadata_list[idx] if idx < len(self.metadata_list) else {}
                out.append(
                    {
                        "parent_id": meta.get("parent_id"),
                        "text": self.corpus[idx] if idx < len(self.corpus) else "",
                        "department": meta.get("department"),
                        "source": meta.get("source"),
                        "permission_label": meta.get("permission_label"),
                        "tags": meta.get("tags") or [],
                        "score": float(scores[idx]),
                    }
                )
            return out

    def fetch_by_parent_ids(self, parent_ids: list[str]) -> dict[str, dict[str, Any]]:
        with _lock:
            if self._parent_by_id is None:
                self._rebuild_parent_index()
            parent_map = self._parent_by_id or {}
            return {pid: dict(parent_map[pid]) for pid in parent_ids if pid in parent_map}


_index: BM25Index | None = None
_loaded_path: str | None = None


def _active_bm25_path() -> Path:
    try:
        from api.vector_store_registry import get_active_bm25_path

        return get_active_bm25_path()
    except Exception:
        return Path(settings.bm25_index_path)


def reload_bm25_index() -> None:
    global _index, _loaded_path
    _index = None
    _loaded_path = None


def get_bm25_index() -> BM25Index:
    global _index, _loaded_path
    path = _active_bm25_path()
    key = str(path.resolve())
    if _index is None or _loaded_path != key:
        _index = BM25Index(path)
        _loaded_path = key
    return _index


def ensure_parent_index() -> None:
    get_bm25_index().index_path.parent.mkdir(parents=True, exist_ok=True)


def delete_parents_by_source(source: str) -> None:
    get_bm25_index().delete_by_source(source)


def index_parent_documents(docs: list[dict[str, Any]]) -> int:
    return get_bm25_index().index_parent_documents(docs)


def bm25_parent_search(
    query: str,
    top_k: int,
    user_department: str | None = None,
) -> list[dict[str, Any]]:
    return get_bm25_index().search(query, top_k=top_k, user_department=user_department)


def fetch_parents_by_ids(parent_ids: list[str]) -> dict[str, dict[str, Any]]:
    return get_bm25_index().fetch_by_parent_ids(parent_ids)
