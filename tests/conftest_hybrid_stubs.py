"""Shared stubs so hybrid_searcher unit tests avoid Milvus / embedding stack."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

_STUBBED_KEYS = (
    "pymilvus",
    "rank_bm25",
    "jieba",
    "FlagEmbedding",
    "sentence_transformers",
    "indexing.embeddings",
    "indexing.dedup_text",
    "indexing.chunk_dedup_store",
    "indexing.es_indexer",
    "indexing.milvus_indexer",
    "chunker",
    "chunker.utils",
)


def install_hybrid_search_stubs() -> dict[str, object | None]:
    """Install stubs; returns prior sys.modules snapshot for teardown."""
    prior = {k: sys.modules.get(k) for k in _STUBBED_KEYS}

    for _mod in ("pymilvus", "rank_bm25", "jieba", "FlagEmbedding", "sentence_transformers"):
        sys.modules.setdefault(_mod, MagicMock())

    emb = types.ModuleType("indexing.embeddings")
    emb.embed_texts = MagicMock(return_value=[])
    emb.embedding_dim = MagicMock(return_value=768)
    sys.modules["indexing.embeddings"] = emb

    dedup_text = types.ModuleType("indexing.dedup_text")
    dedup_text.char_ngram_jaccard = MagicMock(return_value=0.0)
    sys.modules["indexing.dedup_text"] = dedup_text

    chunk_dedup = types.ModuleType("indexing.chunk_dedup_store")
    store = MagicMock()
    store.aliases_for_parent = MagicMock(return_value=[])
    chunk_dedup.get_chunk_dedup_store = MagicMock(return_value=store)
    sys.modules["indexing.chunk_dedup_store"] = chunk_dedup

    es = types.ModuleType("indexing.es_indexer")
    es.bm25_parent_search = MagicMock(return_value=[])
    es.fetch_parents_by_ids = MagicMock(return_value={})
    sys.modules["indexing.es_indexer"] = es

    milvus = types.ModuleType("indexing.milvus_indexer")
    milvus.vector_search = MagicMock(return_value=[])
    sys.modules["indexing.milvus_indexer"] = milvus

    chunker_utils = types.ModuleType("chunker.utils")
    chunker_utils.tags_from_store_value = MagicMock(return_value=[])
    chunker_utils.tags_to_store_value = MagicMock(return_value="")
    sys.modules["chunker"] = types.ModuleType("chunker")
    sys.modules["chunker.utils"] = chunker_utils

    return prior


def restore_hybrid_search_stubs(prior: dict[str, object | None]) -> None:
    for key, old in prior.items():
        if old is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = old  # type: ignore[assignment]
    for name in list(sys.modules):
        if name == "retrieval" or name.startswith("retrieval."):
            sys.modules.pop(name, None)
