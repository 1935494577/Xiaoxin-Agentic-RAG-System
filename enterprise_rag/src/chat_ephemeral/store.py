"""Session-scoped ephemeral document index for Chat temp uploads."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chunker.parent_child import split_parent_child
from config import settings
from indexing.embeddings import embed_texts

_lock = threading.Lock()


@dataclass
class EphemeralDoc:
    doc_id: str
    session_id: str
    user_id: str
    filename: str
    created_at: str
    chunks: list[dict[str, Any]]


def _session_dir(session_id: str) -> Path:
    d = Path(settings.ephemeral_docs_dir) / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _doc_path(session_id: str, doc_id: str) -> Path:
    return _session_dir(session_id) / f"{doc_id}.json"


def save_ephemeral_document(
    *,
    session_id: str,
    user_id: str,
    filename: str,
    text: str,
    department: str | None = None,
) -> EphemeralDoc:
    doc_id = uuid.uuid4().hex[:16]
    source = f"ephemeral:{session_id}:{doc_id}"
    _, children = split_parent_child(text, source, department=department)
    texts = [c.text for c in children]
    vectors: list[list[float]] = []
    if texts:
        mat = embed_texts(texts)
        vectors = mat.tolist()
    chunks: list[dict[str, Any]] = []
    for i, c in enumerate(children):
        chunks.append(
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "vector": vectors[i] if i < len(vectors) else [],
                "source": source,
            }
        )
    doc = EphemeralDoc(
        doc_id=doc_id,
        session_id=session_id,
        user_id=user_id,
        filename=filename,
        created_at=datetime.now(timezone.utc).isoformat(),
        chunks=chunks,
    )
    with _lock:
        _doc_path(session_id, doc_id).write_text(
            json.dumps(asdict(doc), ensure_ascii=False),
            encoding="utf-8",
        )
    return doc


def load_ephemeral_document(session_id: str, doc_id: str) -> EphemeralDoc | None:
    path = _doc_path(session_id, doc_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return EphemeralDoc(**data)
    except Exception:
        return None


def search_ephemeral(
    session_id: str,
    doc_id: str,
    query: str,
    *,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    doc = load_ephemeral_document(session_id, doc_id)
    if not doc or not doc.chunks:
        return []
    if not query.strip():
        return doc.chunks[:top_k]
    q_vec = embed_texts([query])[0]
    scored: list[tuple[float, dict[str, Any]]] = []
    for ch in doc.chunks:
        vec = ch.get("vector") or []
        if not vec:
            continue
        dot = sum(a * b for a, b in zip(q_vec, vec, strict=False))
        scored.append((dot, ch))
    scored.sort(key=lambda x: -x[0])
    out: list[dict[str, Any]] = []
    for score, ch in scored[:top_k]:
        out.append(
            {
                "parent_id": ch.get("chunk_id") or "",
                "text": ch.get("text") or "",
                "source": ch.get("source") or doc.filename,
                "hybrid_score": float(score),
                "department": "",
                "permission_label": "internal",
                "tags": ["ephemeral"],
            }
        )
    return out


def list_ephemeral_docs(session_id: str) -> list[dict[str, str]]:
    d = _session_dir(session_id)
    rows: list[dict[str, str]] = []
    for path in d.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "doc_id": str(data.get("doc_id") or path.stem),
                    "filename": str(data.get("filename") or ""),
                }
            )
        except Exception:
            continue
    return rows
