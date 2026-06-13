"""L2: embedding-based semantic history pruning (no LLM on hot path)."""

from __future__ import annotations

import math
from typing import Any

from indexing.embeddings import embed_texts


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _turn_pairs(history: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Group history into (user, assistant?) pairs in order."""
    pairs: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    i = 0
    while i < len(history):
        m = history[i]
        if str(m.get("role")) != "user":
            i += 1
            continue
        assistant = None
        if i + 1 < len(history) and str(history[i + 1].get("role")) == "assistant":
            assistant = history[i + 1]
            i += 2
        else:
            i += 1
        pairs.append((m, assistant))
    return pairs


def prune_history_by_embedding(
    standalone_query: str,
    history: list[dict[str, Any]],
    *,
    min_similarity: float = 0.35,
    max_turns: int = 4,
) -> list[dict[str, Any]]:
    """
    Keep user+assistant pairs whose user message is semantically close to the query.
    """
    if not history or not (standalone_query or "").strip():
        return []

    pairs = _turn_pairs(history)
    if not pairs:
        return []

    user_texts = [str(u.get("content") or "") for u, _ in pairs]
    vectors = embed_texts([standalone_query.strip()] + user_texts)
    if not vectors or len(vectors) < 2:
        return history[-max(1, max_turns) * 2 :]

    q_vec = vectors[0]
    scored: list[tuple[float, int]] = []
    for idx, u_text in enumerate(user_texts):
        sim = _cosine(q_vec, vectors[idx + 1])
        if sim >= float(min_similarity):
            scored.append((sim, idx))

    if not scored:
        return history[-2:] if len(history) >= 2 else list(history)

    scored.sort(key=lambda x: (-x[0], x[1]))
    keep_indices = sorted(idx for _, idx in scored[: max(1, int(max_turns))])

    out: list[dict[str, Any]] = []
    for idx in keep_indices:
        user_m, asst_m = pairs[idx]
        out.append(user_m)
        if asst_m is not None:
            out.append(asst_m)
    return out
