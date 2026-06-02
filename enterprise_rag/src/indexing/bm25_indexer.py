"""plan1：纯 Python BM25 父块索引（替代 Elasticsearch）。"""

from __future__ import annotations

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
        if self.index_path.is_file():
            self.load()

    def load(self) -> None:
        with self.index_path.open(encoding="utf-8") as f:
            data = json.load(f)
        self.corpus = list(data.get("corpus") or [])
        self.metadata_list = list(data.get("metadata_list") or [])
        self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        if not self.corpus:
            self.bm25 = None
            return
        tokenized = [_tokenize(t) for t in self.corpus]
        self.bm25 = BM25Okapi(tokenized)

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
        """docs: parent_id, content, department, source, permission_label"""
        with _lock:
            for d in docs:
                self.corpus.append(str(d.get("content") or ""))
                self.metadata_list.append(
                    {
                        "parent_id": str(d.get("parent_id", "")),
                        "department": str(d.get("department", "")),
                        "source": str(d.get("source", "")),
                        "permission_label": str(d.get("permission_label", "public")),
                    }
                )
            self._rebuild_bm25()
            self.save()
        return len(docs)

    def search(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        with _lock:
            if not self.bm25 or not self.corpus:
                return []
            q_tok = _tokenize(query)
            scores = self.bm25.get_scores(q_tok)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
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
                        "score": float(scores[idx]),
                    }
                )
            return out

    def fetch_by_parent_ids(self, parent_ids: list[str]) -> dict[str, dict[str, Any]]:
        want = set(parent_ids)
        out: dict[str, dict[str, Any]] = {}
        with _lock:
            for text, meta in zip(self.corpus, self.metadata_list):
                pid = str(meta.get("parent_id", ""))
                if pid in want:
                    out[pid] = {
                        "parent_id": pid,
                        "text": text,
                        "department": meta.get("department"),
                        "source": meta.get("source"),
                        "permission_label": meta.get("permission_label"),
                    }
        return out


_index: BM25Index | None = None


def get_bm25_index() -> BM25Index:
    global _index
    if _index is None:
        _index = BM25Index()
    return _index


def ensure_parent_index() -> None:
    get_bm25_index().index_path.parent.mkdir(parents=True, exist_ok=True)


def delete_parents_by_source(source: str) -> None:
    get_bm25_index().delete_by_source(source)


def index_parent_documents(docs: list[dict[str, Any]]) -> int:
    return get_bm25_index().index_parent_documents(docs)


def bm25_parent_search(query: str, top_k: int) -> list[dict[str, Any]]:
    return get_bm25_index().search(query, top_k=top_k)


def fetch_parents_by_ids(parent_ids: list[str]) -> dict[str, dict[str, Any]]:
    return get_bm25_index().fetch_by_parent_ids(parent_ids)
