"""L1 document-level registry: content_hash → canonical source + aliases."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import settings

_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class DocRecord:
    content_hash: str
    canonical_source: str
    alias_sources: list[str] = field(default_factory=list)
    parent_count: int = 0
    child_count: int = 0
    ingested_at: str = ""
    updated_at: str = ""


class DocumentRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or settings.doc_registry_path)
        self._docs: dict[str, dict[str, Any]] = {}
        self._source_to_hash: dict[str, str] = {}
        if self.path.is_file():
            self._load()

    def _load(self) -> None:
        with self.path.open(encoding="utf-8") as f:
            data = json.load(f)
        self._docs = dict(data.get("docs") or {})
        self._source_to_hash = dict(data.get("source_to_hash") or {})

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"docs": self._docs, "source_to_hash": self._source_to_hash}
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def lookup_by_hash(self, content_hash: str) -> DocRecord | None:
        raw = self._docs.get(content_hash)
        if not raw:
            return None
        return DocRecord(
            content_hash=content_hash,
            canonical_source=str(raw.get("canonical_source") or ""),
            alias_sources=list(raw.get("alias_sources") or []),
            parent_count=int(raw.get("parent_count") or 0),
            child_count=int(raw.get("child_count") or 0),
            ingested_at=str(raw.get("ingested_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
        )

    def lookup_by_source(self, source: str) -> DocRecord | None:
        h = self._source_to_hash.get(source)
        if not h:
            return None
        return self.lookup_by_hash(h)

    def register(
        self,
        source: str,
        content_hash: str,
        *,
        parent_count: int,
        child_count: int,
    ) -> None:
        now = _utc_now()
        with _lock:
            existing = self._docs.get(content_hash)
            if existing:
                existing["canonical_source"] = source
                existing["parent_count"] = parent_count
                existing["child_count"] = child_count
                existing["updated_at"] = now
                if "ingested_at" not in existing or not existing["ingested_at"]:
                    existing["ingested_at"] = now
            else:
                self._docs[content_hash] = {
                    "canonical_source": source,
                    "alias_sources": [],
                    "parent_count": parent_count,
                    "child_count": child_count,
                    "ingested_at": now,
                    "updated_at": now,
                }
            old_hash = self._source_to_hash.get(source)
            if old_hash and old_hash != content_hash:
                self._remove_source_from_doc(old_hash, source)
            self._source_to_hash[source] = content_hash
            self._save()

    def add_alias(self, canonical_source: str, alias_source: str, content_hash: str) -> None:
        now = _utc_now()
        with _lock:
            doc = self._docs.get(content_hash)
            if not doc:
                doc = {
                    "canonical_source": canonical_source,
                    "alias_sources": [],
                    "parent_count": 0,
                    "child_count": 0,
                    "ingested_at": now,
                    "updated_at": now,
                }
                self._docs[content_hash] = doc
            aliases = list(doc.get("alias_sources") or [])
            if alias_source != canonical_source and alias_source not in aliases:
                aliases.append(alias_source)
            doc["alias_sources"] = aliases
            doc["updated_at"] = now
            self._source_to_hash[alias_source] = content_hash
            self._save()

    def unregister_source(self, source: str) -> None:
        with _lock:
            h = self._source_to_hash.pop(source, None)
            if not h:
                self._save()
                return
            self._remove_source_from_doc(h, source)
            self._save()

    def _remove_source_from_doc(self, content_hash: str, source: str) -> None:
        doc = self._docs.get(content_hash)
        if not doc:
            return
        if str(doc.get("canonical_source") or "") == source:
            aliases = list(doc.get("alias_sources") or [])
            if aliases:
                doc["canonical_source"] = aliases.pop(0)
                doc["alias_sources"] = aliases
            else:
                self._docs.pop(content_hash, None)
                return
        else:
            aliases = [a for a in doc.get("alias_sources") or [] if a != source]
            doc["alias_sources"] = aliases


_registry: DocumentRegistry | None = None


def get_document_registry() -> DocumentRegistry:
    global _registry
    if _registry is None:
        _registry = DocumentRegistry()
    return _registry


def reset_document_registry() -> None:
    global _registry
    _registry = None
