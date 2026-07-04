"""Tests for domain term embedding neighbors (Tier 2)."""

from __future__ import annotations

import json
from unittest.mock import patch

import numpy as np
import pytest

from retrieval import term_embeddings


@pytest.fixture
def lexicon_env(tmp_path, monkeypatch):
    path = tmp_path / "domain_lexicon.json"
    path.write_text(
        json.dumps({"terms": {"感知力": {"sources": ["a"]}, "感知能力训练": {"sources": ["a"]}}, "updated_at": "t1"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("retrieval.domain_lexicon._lexicon_path", lambda: path)
    term_embeddings.invalidate_term_embedding_cache()
    return path


def test_nearest_terms_by_embedding(lexicon_env):
    def fake_embed(texts):
        vecs = []
        for t in texts:
            if "感知力" in t and "训练" not in t:
                vecs.append(np.array([1.0, 0.0], dtype=np.float32))
            elif "感知能力训练" in t:
                vecs.append(np.array([0.95, 0.05], dtype=np.float32))
            else:
                vecs.append(np.array([0.0, 1.0], dtype=np.float32))
        return np.stack(vecs)

    with patch.object(term_embeddings, "embed_texts", side_effect=fake_embed):
        hits = term_embeddings.nearest_domain_terms("什么是感知力", top_k=2, min_sim=0.8)
    assert "感知能力训练" in hits


def test_neighbors_disabled(monkeypatch, lexicon_env):
    monkeypatch.setattr("retrieval.term_embeddings.settings.domain_embedding_neighbors_enabled", False)
    assert term_embeddings.nearest_domain_terms("感知力") == []
