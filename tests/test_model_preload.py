"""Model preload warmup behavior."""

import numpy as np

from indexing.model_preload import _model_ids, warmup_models_in_memory


def test_warmup_skips_reranker_when_disabled(monkeypatch):
    calls: list[str] = []

    def _embed(*a, **k):
        calls.append("embed")
        return np.zeros((1, 8), dtype=np.float32)

    def _rerank(*a, **k):
        calls.append("rerank")
        return []

    monkeypatch.setattr("indexing.embeddings.embed_texts", _embed)
    monkeypatch.setattr("retrieval.reranker.rerank_parents", _rerank)

    from config import settings

    monkeypatch.setattr(settings, "warmup_reranker_on_startup", False)
    warmup_models_in_memory()
    assert calls == ["embed"]

    calls.clear()
    monkeypatch.setattr(settings, "warmup_reranker_on_startup", True)
    warmup_models_in_memory()
    assert calls == ["embed", "rerank"]


def test_model_ids_skips_reranker_when_warmup_disabled(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "embedding_model", "BAAI/bge-small-zh-v1.5")
    monkeypatch.setattr(settings, "embedding_st_fallback", "BAAI/bge-small-zh-v1.5")
    monkeypatch.setattr(settings, "reranker_model", "BAAI/bge-reranker-base")
    monkeypatch.setattr(settings, "warmup_reranker_on_startup", False)
    assert _model_ids() == ["BAAI/bge-small-zh-v1.5"]
