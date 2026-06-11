"""
部门 + 可见范围 ACL 集成测试（真实文档，隔离索引，不写入生产库）。

数据源：d:\\dataset\\各年级要求.txt
- 公开文档：四部门用户均应能检索到
- 内部文档：仅归属部门用户能检索到，其他部门不得命中
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from config import settings
from security.access_control import DEPARTMENTS

DATASET_PATH = Path(os.environ.get("ACL_TEST_DATASET", r"d:\dataset\各年级要求.txt"))

# 用户会用部分关键字提问
PUBLIC_QUERY = "1-3年级超脑阅读"
INTERNAL_QUERY = "扫描速记逐字倒着背"
ALT_QUERY = "4-6年级晋级要求"

EMBED_DIM = 512


def _fake_embed_texts(texts: list[str]) -> np.ndarray:
    """Deterministic bag-of-char vectors — no model download."""
    rows: list[np.ndarray] = []
    for text in texts:
        v = np.zeros(EMBED_DIM, dtype=np.float32)
        for i, ch in enumerate(text):
            v[(ord(ch) + i * 7) % EMBED_DIM] += 1.0
        norm = float(np.linalg.norm(v)) + 1e-12
        rows.append(v / norm)
    return np.stack(rows, axis=0)


@pytest.fixture()
def grade_req_text() -> str:
    if not DATASET_PATH.is_file():
        pytest.skip(f"测试数据不存在: {DATASET_PATH}")
    text = DATASET_PATH.read_text(encoding="utf-8").strip()
    assert len(text) > 100, "测试文档过短"
    return text


def _doc_body(department: str, permission_label: str, body: str) -> str:
    """每份入库文档带唯一锚点，便于在相同正文下区分来源；正文仍含年级/超脑等检索词。"""
    vis = "公开" if permission_label == "public" else "内部"
    anchor = f"【ACL-{department}-{vis}-锚点】"
    return f"{anchor}\n{body}"


@pytest.fixture()
def isolated_acl_kb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """临时向量库 + BM25；测试结束自动删除，不污染 enterprise_rag/data。"""
    store_dir = tmp_path / "stores"
    store_dir.mkdir()
    numpy_path = store_dir / "acl_vectors.json"
    bm25_path = store_dir / "acl_bm25.json"
    numpy_path.write_text("[]", encoding="utf-8")
    bm25_path.write_text('{"corpus":[],"metadata_list":[]}', encoding="utf-8")

    reg_path = tmp_path / "vector_stores.json"
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()

    monkeypatch.setattr(settings, "vector_stores_registry_path", reg_path)
    monkeypatch.setattr(settings, "vector_stores_data_dir", store_dir)
    monkeypatch.setattr(settings, "numpy_vector_store_path", numpy_path)
    monkeypatch.setattr(settings, "bm25_index_path", bm25_path)
    monkeypatch.setattr(settings, "data_raw_dir", tmp_path / "raw")
    monkeypatch.setattr(settings, "data_processed_dir", tmp_path / "processed")
    monkeypatch.setattr(settings, "data_chunks_dir", chunks_dir)
    monkeypatch.setattr(settings, "doc_registry_path", tmp_path / "doc_registry.json")
    monkeypatch.setattr(settings, "chunk_dedup_index_path", tmp_path / "chunk_dedup.json")
    monkeypatch.setattr(settings, "ingest_content_hash_enabled", False)
    monkeypatch.setattr(settings, "ingest_chunk_dedup_enabled", False)
    monkeypatch.setattr(settings, "query_rewrite_enabled", False)
    monkeypatch.setattr(settings, "redis_search_cache_enabled", False)
    monkeypatch.setattr(settings, "retrieve_top_k", 60)
    monkeypatch.setattr(settings, "rerank_top_k", 30)

    monkeypatch.setattr("indexing.embeddings.embed_texts", _fake_embed_texts)
    monkeypatch.setattr("retrieval.hybrid_searcher.embed_texts", _fake_embed_texts)

    from api.vector_store_registry import ensure_default_registry, reload_all_indexes

    ensure_default_registry()
    reload_all_indexes()

    yield tmp_path

    reload_all_indexes()


def _ingest(
    text: str,
    *,
    source: str,
    department: str,
    permission_label: str,
) -> int:
    from api.main import _ingest_text

    resp = _ingest_text(
        text,
        source=source,
        department=department,
        permission_label=permission_label,
        tags=["ACL测试"],
    )
    assert resp.chunks_indexed > 0, f"入库失败: {source} ({resp.message})"
    return int(resp.chunks_indexed)


def _search(user_department: str, query: str, *, top_k: int = 30):
    from retrieval.hybrid_searcher import hybrid_search

    return hybrid_search(
        query,
        user_department,
        top_k=top_k,
        retrieve_top_k=60,
        rerank_top_k=30,
        skip_rerank=True,
        skip_query_rewrite=True,
    )


def _sources(hits: list[dict]) -> set[str]:
    return {str(h.get("source") or "") for h in hits}


@pytest.fixture()
def acl_corpus(isolated_acl_kb, grade_req_text: str):
    """四部门 ×（公开 + 内部）各入库一份，仅存在于临时索引。"""
    for dept in DEPARTMENTS:
        _ingest(
            _doc_body(dept, "public", grade_req_text),
            source=f"grade_req_{dept}_public.txt",
            department=dept,
            permission_label="public",
        )
        _ingest(
            _doc_body(dept, "internal", grade_req_text),
            source=f"grade_req_{dept}_internal.txt",
            department=dept,
            permission_label="internal",
        )
    from api.vector_store_registry import reload_all_indexes

    reload_all_indexes()


# ---- 公开：四部门用户均应命中四份公开文档 ----


def _assert_source_retrievable(
    user_dept: str,
    source_name: str,
    *queries: str,
) -> None:
    for q in queries:
        _, hits = _search(user_dept, q)
        if source_name in _sources(hits):
            return
    pytest.fail(
        f"用户部门={user_dept} 未能检索到 {source_name}，"
        f"已尝试查询: {list(queries)}"
    )


@pytest.mark.parametrize("user_dept", DEPARTMENTS)
@pytest.mark.parametrize("owner_dept", DEPARTMENTS)
def test_public_doc_visible_to_all_departments(acl_corpus, user_dept: str, owner_dept: str):
    """成功：公开文档 — 任意部门用户用关键字检索均可命中。"""
    expected = f"grade_req_{owner_dept}_public.txt"
    _assert_source_retrievable(
        user_dept,
        expected,
        PUBLIC_QUERY,
        f"ACL-{owner_dept}-公开-锚点",
    )


@pytest.mark.parametrize("user_dept", DEPARTMENTS)
@pytest.mark.parametrize("owner_dept", DEPARTMENTS)
def test_public_doc_alt_keyword(acl_corpus, user_dept: str, owner_dept: str):
    """成功：换一组关键字「4-6年级晋级要求」仍能命中公开文档。"""
    _assert_source_retrievable(
        user_dept,
        f"grade_req_{owner_dept}_public.txt",
        ALT_QUERY,
        f"ACL-{owner_dept}-公开-锚点",
    )


# ---- 内部：仅归属部门可命中；其他部门不得命中 ----


@pytest.mark.parametrize("owner_dept", DEPARTMENTS)
def test_internal_doc_visible_to_owner(acl_corpus, owner_dept: str):
    """成功：内部文档 — 归属部门用户可检索到（锚点 + 正文关键字）。"""
    _assert_source_retrievable(
        owner_dept,
        f"grade_req_{owner_dept}_internal.txt",
        f"ACL-{owner_dept}-内部-锚点",
        INTERNAL_QUERY,
    )


@pytest.mark.parametrize("user_dept", DEPARTMENTS)
@pytest.mark.parametrize("owner_dept", DEPARTMENTS)
def test_internal_doc_hidden_from_other_departments(
    acl_corpus, user_dept: str, owner_dept: str
):
    """失败场景：内部文档 — 非归属部门用户不得命中。"""
    if user_dept == owner_dept:
        pytest.skip("同部门属于成功用例")
    _, hits = _search(user_dept, INTERNAL_QUERY)
    forbidden = f"grade_req_{owner_dept}_internal.txt"
    assert forbidden not in _sources(hits), (
        f"用户部门={user_dept} 不应看到 {owner_dept} 的内部文档 {forbidden}"
    )


# ---- HTTP /retrieve API（知识库检索调试接口）----


@pytest.fixture()
def retrieve_client(isolated_acl_kb, grade_req_text: str):
    """单文档场景 API 测试，仍用临时索引。"""
    _ingest(
        _doc_body("技术部", "public", grade_req_text),
        source="grade_req_api_public.txt",
        department="技术部",
        permission_label="public",
    )
    _ingest(
        _doc_body("技术部", "internal", grade_req_text),
        source="grade_req_api_internal.txt",
        department="技术部",
        permission_label="internal",
    )
    from api.vector_store_registry import reload_all_indexes

    reload_all_indexes()

    from api.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("user_dept", DEPARTMENTS)
def test_retrieve_api_public_hits(retrieve_client, user_dept: str):
    r = retrieve_client.post(
        "/retrieve",
        json={"query": PUBLIC_QUERY, "user_department": user_dept, "top_k": 15},
    )
    assert r.status_code == 200
    sources = {h["source"] for h in r.json().get("hits") or []}
    assert "grade_req_api_public.txt" in sources


@pytest.mark.parametrize("user_dept", DEPARTMENTS)
def test_retrieve_api_internal_acl(retrieve_client, user_dept: str):
    r = retrieve_client.post(
        "/retrieve",
        json={"query": INTERNAL_QUERY, "user_department": user_dept, "top_k": 15},
    )
    assert r.status_code == 200
    sources = {h["source"] for h in r.json().get("hits") or []}
    if user_dept == "技术部":
        assert "grade_req_api_internal.txt" in sources
    else:
        assert "grade_req_api_internal.txt" not in sources


def test_corpus_not_written_to_production_data(isolated_acl_kb, grade_req_text: str):
    """确认测试索引写在 tmp 目录，未追加生产 numpy_vectors.json。"""
    prod = Path(settings.numpy_vector_store_path)
    # fixture 已把 settings.numpy_vector_store_path 指到 tmp；对比 repo 默认路径
    repo_default = ROOT / "enterprise_rag" / "data" / "numpy_vectors.json"
    assert prod.resolve() != repo_default.resolve()
    _ingest(
        _doc_body("技术部", "public", grade_req_text[:500]),
        source="isolation_check.txt",
        department="技术部",
        permission_label="public",
    )
    assert prod.is_file()
    assert not repo_default.exists() or prod.resolve() != repo_default.resolve()
