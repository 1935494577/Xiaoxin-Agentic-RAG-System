"""Delete ingested source tests."""

from __future__ import annotations

from indexing.document_registry import DocumentRegistry
from indexing.source_delete import delete_ingested_source


def test_delete_ingested_source_removes_registry(tmp_path, monkeypatch):
    db = tmp_path / "doc_registry.json"
    reg = DocumentRegistry(db)
    reg.register("notes.txt", "hash1", parent_count=2, child_count=4)

    monkeypatch.setattr("indexing.source_delete.get_document_registry", lambda: reg)
    monkeypatch.setattr("indexing.milvus_indexer.delete_by_source", lambda s: None)
    monkeypatch.setattr("indexing.es_indexer.delete_parents_by_source", lambda s: None)
    monkeypatch.setattr("graph.store.delete_edges_by_source", lambda s: None)
    monkeypatch.setattr("config.settings.ingest_chunk_dedup_enabled", False)

    assert delete_ingested_source("notes.txt") is True
    assert reg.lookup_by_source("notes.txt") is None
    assert delete_ingested_source("notes.txt") is False


def test_delete_ingested_source_unknown_returns_false(tmp_path, monkeypatch):
    reg = DocumentRegistry(tmp_path / "doc_registry.json")
    monkeypatch.setattr("indexing.source_delete.get_document_registry", lambda: reg)
    assert delete_ingested_source("missing.txt") is False
