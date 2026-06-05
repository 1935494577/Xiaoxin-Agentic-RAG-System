"""Ensure embedding/reranker weights exist on disk before first request; optional warm load."""

from __future__ import annotations

import logging

from config import settings
from indexing.modelscope_hub import resolve_model_path

logger = logging.getLogger(__name__)


def _model_ids() -> list[str]:
    out: list[str] = []
    for raw in (settings.embedding_model, settings.reranker_model):
        s = str(raw).strip()
        if s and "/" in s:
            out.append(s)
    fb = (settings.embedding_st_fallback or "").strip()
    if fb and "/" in fb and fb not in out:
        out.append(fb)
    return out


def ensure_models_on_disk() -> None:
    """Download missing weights to local cache; no-op when files already present."""
    for model_id in _model_ids():
        path = resolve_model_path(model_id, download_if_missing=True)
        logger.info("Model ready on disk: %s -> %s", model_id, path)


def warmup_models_in_memory() -> None:
    """Load embedding/reranker once at startup so ingest/chat do not pay cold-start."""
    from indexing.embeddings import embed_texts
    from retrieval.reranker import rerank_parents

    embed_texts(["warmup"], batch_size=1)
    rerank_parents("warmup", [{"text": "warmup"}], top_k=1)
    logger.info("Embedding and reranker models warmed up in memory")
