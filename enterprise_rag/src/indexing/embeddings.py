from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from config import settings
from runtime_device import use_fp16_safe, torch_device_string


def _hf_cache_dir() -> str | None:
    raw = (settings.hf_hub_cache or "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def _st_local_kw() -> dict[str, Any]:
    kw: dict[str, Any] = {"trust_remote_code": True}
    cd = _hf_cache_dir()
    if cd:
        kw["cache_folder"] = cd
    if settings.hf_local_files_only:
        kw["local_files_only"] = True
    return kw


def _embed_flag(texts: list[str], batch_size: int) -> np.ndarray:
    model = _flag_model()
    emb = model.encode(texts, batch_size=batch_size)
    return np.asarray(emb, dtype=np.float32)


def _embed_st(texts: list[str], batch_size: int) -> np.ndarray:
    return _embed_st_named(texts, batch_size, settings.embedding_model)


def _embed_st_named(texts: list[str], batch_size: int, model_name: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = _st_model_named(model_name.strip())
    emb = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(emb, dtype=np.float32)


@lru_cache
def _flag_model():
    """按模型名自动选 BGEM3FlagModel / FlagModel，并支持 cache_dir。"""
    from FlagEmbedding import FlagAutoModel

    model_path = settings.embedding_model
    if settings.use_modelscope_download:
        from indexing.modelscope_hub import resolve_model_path

        model_path = resolve_model_path(settings.embedding_model, download_if_missing=False)

    kw: dict[str, Any] = {
        "model_name_or_path": model_path,
        "normalize_embeddings": True,
        "use_fp16": use_fp16_safe(),
        "trust_remote_code": True,
    }
    cd = _hf_cache_dir()
    if cd:
        kw["cache_dir"] = cd
    return FlagAutoModel.from_finetuned(**kw)


@lru_cache
def _st_model():
    return _st_model_named(settings.embedding_model)


@lru_cache
def _st_model_named(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        model_name,
        device=torch_device_string(),
        **_st_local_kw(),
    )


def embed_texts(texts: list[str], batch_size: int | None = None) -> np.ndarray:
    """嵌入：auto 时先 Flag 再 sentence-transformers；可配置仅 ST 以减轻下载/显存压力。"""
    if not texts:
        return np.zeros((0, embedding_dim()), dtype=np.float32)
    bs = batch_size or settings.embedding_batch_size
    mode = (settings.embedding_backend or "auto").strip().lower()
    if mode == "sentence_transformers":
        out = _embed_st(texts, bs)
    elif mode == "flag":
        out = _embed_flag(texts, bs)
    else:
        try:
            out = _embed_flag(texts, bs)
        except Exception:
            fb = (settings.embedding_st_fallback or "BAAI/bge-small-zh-v1.5").strip()
            out = _embed_st_named(texts, bs, fb)
    norms = np.linalg.norm(out, axis=1, keepdims=True) + 1e-12
    return (out / norms).astype(np.float32)


def embedding_dim() -> int:
    mode = (settings.embedding_backend or "auto").strip().lower()
    if mode == "sentence_transformers":
        return int(_st_model().get_sentence_embedding_dimension())
    if mode == "flag":
        v = _flag_model().encode(["ping"], batch_size=1)
        return int(np.asarray(v).shape[-1])
    try:
        v = _flag_model().encode(["ping"], batch_size=1)
        return int(np.asarray(v).shape[-1])
    except Exception:
        fb = (settings.embedding_st_fallback or "BAAI/bge-small-zh-v1.5").strip()
        return int(_st_model_named(fb).get_sentence_embedding_dimension())
