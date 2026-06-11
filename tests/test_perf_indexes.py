"""Correctness tests for index-layer performance optimizations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from config import settings
from indexing.bm25_indexer import BM25Index
from indexing import numpy_vector_index as nvi


def _make_unit_vectors(n: int, dim: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    mat = rng.standard_normal((n, dim)).astype(np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
    return mat / norms


@pytest.fixture
def numpy_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = tmp_path / "vecs.json"
    monkeypatch.setattr(settings, "numpy_vector_store_path", store)
    nvi.reload_store()
    yield store
    nvi.reload_store()


def test_numpy_vector_search_returns_top_by_similarity(numpy_store: Path):
    dim = 8
    vecs = _make_unit_vectors(5, dim, seed=1)
    rows = []
    for i, v in enumerate(vecs):
        rows.append(
            {
                "id": f"id{i}",
                "vector": v.tolist(),
                "text": f"text-{i}",
                "parent_id": f"p{i}",
                "department": "general" if i != 3 else "hr",
                "source": "doc",
                "tags": "",
            }
        )
    numpy_store.write_text(json.dumps(rows), encoding="utf-8")
    nvi.reload_store()

    query = vecs[2].tolist()
    hits = nvi.vector_search(query, top_k=3, user_department="general")
    assert len(hits) == 3
    assert hits[0]["parent_id"] == "p2"
    assert hits[0]["score"] >= hits[1]["score"] >= hits[2]["score"]

    hr_hits = nvi.vector_search(query, top_k=5, user_department="hr")
    assert len(hr_hits) == 1
    assert hr_hits[0]["parent_id"] == "p3"


def test_numpy_vector_search_after_insert(numpy_store: Path):
    dim = 4
    v0 = _make_unit_vectors(1, dim)[0]
    nvi.insert_child_vectors(
        ids=["a"],
        vectors=[v0.tolist()],
        texts=["hello"],
        parent_ids=["pa"],
        departments=["general"],
        sources=["s"],
    )
    hits = nvi.vector_search(v0.tolist(), top_k=1)
    assert hits[0]["parent_id"] == "pa"


def test_bm25_search_top_k_order(tmp_path: Path):
    idx = BM25Index(tmp_path / "bm25.json")
    docs = [
        {
            "parent_id": f"p{i}",
            "content": f"企业制度 文档编号 {i}",
            "department": "general",
            "source": "s",
            "permission_label": "public",
            "tags": [],
        }
        for i in range(30)
    ]
    idx.index_parent_documents(docs)
    hits = idx.search("企业制度", top_k=5)
    assert len(hits) == 5
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_bm25_fetch_by_parent_ids(tmp_path: Path):
    idx = BM25Index(tmp_path / "bm25.json")
    docs = [
        {
            "parent_id": "alpha",
            "content": "alpha content",
            "department": "general",
            "source": "s",
            "permission_label": "public",
            "tags": [],
        },
        {
            "parent_id": "beta",
            "content": "beta content",
            "department": "general",
            "source": "s",
            "permission_label": "public",
            "tags": [],
        },
    ]
    idx.index_parent_documents(docs)
    fetched = idx.fetch_by_parent_ids(["beta", "missing", "alpha"])
    assert set(fetched) == {"alpha", "beta"}
    assert fetched["alpha"]["text"] == "alpha content"
    assert fetched["beta"]["text"] == "beta content"
