"""Remove an ingested document source from indexes and registry."""

from __future__ import annotations

from config import settings
from indexing.document_registry import get_document_registry


def delete_ingested_source(source: str) -> bool:
    """Purge vectors, BM25 parents, dedup entries, graph edges, and registry row."""
    src = (source or "").strip()
    if not src:
        return False

    registry = get_document_registry()
    if registry.lookup_by_source(src) is None:
        return False

    from graph.store import delete_edges_by_source
    from indexing.es_indexer import delete_parents_by_source
    from indexing.milvus_indexer import delete_by_source as milvus_delete_by_source

    milvus_delete_by_source(src)
    delete_parents_by_source(src)
    delete_edges_by_source(src)

    if settings.ingest_chunk_dedup_enabled:
        from indexing.chunk_dedup_store import get_chunk_dedup_store

        get_chunk_dedup_store().remove_by_source(src)

    registry.unregister_source(src)
    return True
