"""Vector store registry tests."""

import json

import pytest

from api.vector_store_registry import (
    BACKEND_NUMPY,
    activate_store,
    create_store,
    ensure_default_registry,
    get_active_store,
    load_registry,
    validate_insert_vectors,
)
from config import settings


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


def test_ensure_default_registry(registry_env):
    ensure_default_registry()
    reg = load_registry()
    assert len(reg["stores"]) == 1
    assert reg["active_store_id"]


def test_create_and_activate_store(registry_env, monkeypatch):
    monkeypatch.setattr(
        "api.vector_store_registry._current_embedding_meta",
        lambda: ("BAAI/bge-m3", 1024),
    )
    ensure_default_registry()
    row = create_store(name="m3-1024", backend=BACKEND_NUMPY)
    assert row["embedding_dim"] == 1024
    activated = activate_store(row["id"])
    assert activated["active"] is True
    assert get_active_store()["id"] == row["id"]


def test_validate_insert_dim_mismatch(registry_env, monkeypatch):
    monkeypatch.setattr(
        "api.vector_store_registry._current_embedding_meta",
        lambda: ("BAAI/bge-m3", 1024),
    )
    ensure_default_registry()
    legacy = registry_env / "legacy_vectors.json"
    legacy.write_text(
        json.dumps(
            [{"id": "1", "vector": [0.0] * 512, "text": "x", "parent_id": "p", "department": "d", "source": "s"}]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="512"):
        validate_insert_vectors([[0.0] * 1024])
