"""BM25 + NumPy vector ACL filtering with department/visibility."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from config import settings  # noqa: E402
from indexing.bm25_indexer import BM25Index  # noqa: E402
from indexing import numpy_vector_index as nvi  # noqa: E402


def _unit_vec(dim: int, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return (v / (np.linalg.norm(v) + 1e-12)).tolist()


@pytest.fixture
def numpy_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = tmp_path / "vecs.json"
    monkeypatch.setattr(settings, "numpy_vector_store_path", store)
    monkeypatch.setattr("api.vector_store_registry.get_active_numpy_path", lambda: store)
    monkeypatch.setattr("api.vector_store_registry.assert_search_compatible", lambda _d: None)
    monkeypatch.setattr("api.vector_store_registry.validate_insert_vectors", lambda _v: None)
    nvi.reload_store()
    yield store
    nvi.reload_store()


def test_numpy_acl_public_cross_department(numpy_store: Path):
    dim = 8
    rows = [
        {
            "id": "i1",
            "vector": _unit_vec(dim, 1),
            "text": "tech internal",
            "parent_id": "p-tech",
            "department": "技术部",
            "permission_label": "internal",
            "source": "a",
            "tags": "",
        },
        {
            "id": "p1",
            "vector": _unit_vec(dim, 2),
            "text": "media public",
            "parent_id": "p-pub",
            "department": "媒体部",
            "permission_label": "public",
            "source": "b",
            "tags": "",
        },
    ]
    numpy_store.write_text(json.dumps(rows), encoding="utf-8")
    nvi.reload_store()

    q = _unit_vec(dim, 2)
    hits = nvi.vector_search(q, top_k=5, user_department="技术部")
    pids = {h["parent_id"] for h in hits}
    assert "p-pub" in pids
    assert "p-tech" in pids

    ops_hits = nvi.vector_search(q, top_k=5, user_department="运营部")
    ops_pids = {h["parent_id"] for h in ops_hits}
    assert "p-pub" in ops_pids
    assert "p-tech" not in ops_pids


def test_bm25_acl_filters_by_department_and_visibility(tmp_path: Path):
    idx = BM25Index(tmp_path / "bm25.json")
    docs = [
        {
            "parent_id": "tech-in",
            "content": "技术部内部扫描规范",
            "department": "技术部",
            "source": "a",
            "permission_label": "internal",
            "tags": [],
        },
        {
            "parent_id": "media-pub",
            "content": "媒体部公开扫描规范",
            "department": "媒体部",
            "source": "b",
            "permission_label": "public",
            "tags": [],
        },
        {
            "parent_id": "ops-in",
            "content": "运营部内部扫描规范",
            "department": "运营部",
            "source": "c",
            "permission_label": "internal",
            "tags": [],
        },
    ]
    idx.index_parent_documents(docs)

    tech_hits = idx.search("扫描规范", top_k=10, user_department="技术部")
    tech_ids = {h["parent_id"] for h in tech_hits}
    assert tech_ids == {"tech-in", "media-pub"}

    ops_hits = idx.search("扫描规范", top_k=10, user_department="运营部")
    ops_ids = {h["parent_id"] for h in ops_hits}
    assert ops_ids == {"media-pub", "ops-in"}
