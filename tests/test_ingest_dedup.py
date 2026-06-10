"""Unit tests for L1/L2/L3 ingest and retrieval dedup."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chunker.parent_child import split_parent_child
from indexing.chunk_dedup_store import ChunkDedupStore, reset_chunk_dedup_store
from indexing.dedup_text import char_ngram_jaccard, content_hash, hamming64, simhash64
from indexing.document_registry import DocumentRegistry, reset_document_registry
from indexing.ingest_dedup import (
    check_document_duplicate,
    filter_parent_child_duplicates,
    prepare_source_reingest,
)
from retrieval.result_dedup import deduplicate_retrieval_results


@pytest.fixture
def tmp_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reg_path = tmp_path / "doc_registry.json"
    chunk_path = tmp_path / "chunk_dedup.json"
    monkeypatch.setattr("indexing.document_registry.settings.doc_registry_path", reg_path)
    monkeypatch.setattr("indexing.chunk_dedup_store.settings.chunk_dedup_index_path", chunk_path)
    monkeypatch.setattr("indexing.ingest_dedup.settings.doc_registry_path", reg_path)
    monkeypatch.setattr("indexing.ingest_dedup.settings.chunk_dedup_index_path", chunk_path)
    reset_document_registry()
    reset_chunk_dedup_store()
    yield tmp_path
    reset_document_registry()
    reset_chunk_dedup_store()


def test_content_hash_stable():
    a = content_hash("Hello  World\n\n")
    b = content_hash("hello world")
    assert a == b
    assert a.startswith("sha256:")


def test_simhash_near_duplicate():
    t1 = "超脑阅读要求每分钟阅读一千字以上，并保持理解率。"
    t2 = "超脑阅读要求每分钟阅读一千字以上，并保持理解率！"  # tiny edit
    assert hamming64(simhash64(t1), simhash64(t2)) <= 5


def test_char_ngram_jaccard_identical():
    text = "扫描速记逐字倒着背需要注意节奏与准确性"
    assert char_ngram_jaccard(text, text) == 1.0


def test_l1_document_duplicate_skips_embed(tmp_registry: Path):
    text = "同一份培训文档内容 A" * 20
    reg = DocumentRegistry()
    reg.register("canonical.txt", content_hash(text), parent_count=1, child_count=2)

    plan = check_document_duplicate(text, "duplicate.txt")
    assert plan is not None
    assert plan.early_exit is True
    assert plan.stats.doc_duplicate is True
    assert plan.stats.canonical_source == "canonical.txt"

    again = check_document_duplicate(text, "another.txt")
    assert again is not None
    assert again.early_exit is True


def test_l2_parent_chunk_dedup(tmp_registry: Path):
    text = "父块一内容。" * 50 + "\n\n" + "父块二内容。" * 50
    parents, children = split_parent_child(text, "first.txt", department="技术")
    plan1 = filter_parent_child_duplicates(parents, children, "first.txt")
    assert plan1.stats.indexed_children == len(children)

    parents2, children2 = split_parent_child(text, "second.txt", department="技术")
    plan2 = filter_parent_child_duplicates(parents2, children2, "second.txt")
    assert plan2.stats.skipped_parents >= 1
    assert plan2.stats.indexed_children < len(children2)


def test_l3_retrieval_dedup_removes_text_dup():
    rows = [
        {"parent_id": "p1", "text": "超脑阅读每分钟一千字", "hybrid_score": 0.9},
        {"parent_id": "p2", "text": "超脑阅读每分钟一千字", "hybrid_score": 0.8},
        {"parent_id": "p3", "text": "影像追忆需要看完五千字", "hybrid_score": 0.7},
    ]
    out, stats = deduplicate_retrieval_results(rows, top_k=3, enabled=True)
    assert stats["removed_text_dup"] >= 1
    assert len(out) <= 3
    texts = [r["text"] for r in out]
    assert texts.count("超脑阅读每分钟一千字") == 1


def test_prepare_source_reingest_clears_chunk_store(tmp_registry: Path):
    store = ChunkDedupStore()
    store.register("块内容测试" * 10, "p_abc", "old.txt", department="技术")
    prepare_source_reingest("old.txt")
    store2 = ChunkDedupStore()
    assert store2.find_near_duplicate("块内容测试" * 10, department="技术") is None


def test_document_registry_persistence(tmp_path: Path):
    path = tmp_path / "reg.json"
    reg = DocumentRegistry(path)
    reg.register("a.txt", "sha256:abc", parent_count=2, child_count=4)
    reg.add_alias("a.txt", "b.txt", "sha256:abc")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source_to_hash"]["b.txt"] == "sha256:abc"
