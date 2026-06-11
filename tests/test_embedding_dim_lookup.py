"""Embedding dim lookup without loading weights."""

import pytest

from api.vector_store_registry import ensure_default_registry, load_registry
from config import settings
from indexing.embeddings import known_embedding_dim


@pytest.fixture()
def registry_env(tmp_path, monkeypatch):
    reg = tmp_path / "vector_stores.json"
    store_dir = tmp_path / "stores"
    store_dir.mkdir()
    monkeypatch.setattr(settings, "vector_stores_registry_path", reg)
    monkeypatch.setattr(settings, "vector_stores_data_dir", store_dir)
    monkeypatch.setattr(settings, "numpy_vector_store_path", tmp_path / "legacy_vectors.json")
    monkeypatch.setattr(settings, "bm25_index_path", tmp_path / "legacy_bm25.json")
    (tmp_path / "legacy_vectors.json").write_text("[]", encoding="utf-8")
    return tmp_path


def test_known_embedding_dim_bge_small():
    assert known_embedding_dim("BAAI/bge-small-zh-v1.5") == 512


def test_known_embedding_dim_modelscope_escape():
    assert known_embedding_dim("BAAI/bge-small-zh-v1___5") == 512


def test_known_embedding_dim_unknown():
    assert known_embedding_dim("unknown/model-x") is None


def test_ensure_default_registry_skips_model_load(registry_env, monkeypatch):
    """First registry init must not load torch/ST weights for known models."""

    def _boom():
        raise AssertionError("embedding_dim should not be called for bge-small-zh-v1.5")

    monkeypatch.setattr(settings, "embedding_model", "BAAI/bge-small-zh-v1.5")
    monkeypatch.setattr("indexing.embeddings.embedding_dim", _boom)
    ensure_default_registry()
    reg = load_registry()
    assert reg["stores"][0]["embedding_dim"] == 512
