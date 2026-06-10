"""L2 parent-chunk simhash index: canonical parent_id + alias sources."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import settings
from indexing.dedup_text import hamming64, preview_fingerprint, simhash64

_lock = threading.Lock()


@dataclass
class ChunkDedupEntry:
    simhash: int
    parent_id: str
    canonical_source: str
    alias_sources: list[str] = field(default_factory=list)
    department: str = ""
    text_preview_hash: str = ""


class ChunkDedupStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or settings.chunk_dedup_index_path)
        self._entries: list[dict[str, Any]] = []
        if self.path.is_file():
            self._load()

    def _load(self) -> None:
        with self.path.open(encoding="utf-8") as f:
            data = json.load(f)
        self._entries = list(data.get("entries") or [])

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump({"entries": self._entries}, f, ensure_ascii=False, indent=2)

    def _to_entry(self, raw: dict[str, Any]) -> ChunkDedupEntry:
        return ChunkDedupEntry(
            simhash=int(raw.get("simhash") or 0),
            parent_id=str(raw.get("parent_id") or ""),
            canonical_source=str(raw.get("canonical_source") or ""),
            alias_sources=list(raw.get("alias_sources") or []),
            department=str(raw.get("department") or ""),
            text_preview_hash=str(raw.get("text_preview_hash") or ""),
        )

    def find_near_duplicate(
        self,
        text: str,
        *,
        department: str | None = None,
        max_hamming: int | None = None,
    ) -> ChunkDedupEntry | None:
        threshold = (
            max_hamming
            if max_hamming is not None
            else settings.ingest_chunk_simhash_max_hamming
        )
        sh = simhash64(text)
        fp = preview_fingerprint(text)
        dept = department or ""
        best: ChunkDedupEntry | None = None
        best_dist = threshold + 1
        for raw in self._entries:
            if dept and str(raw.get("department") or "") != dept:
                continue
            dist = hamming64(sh, int(raw.get("simhash") or 0))
            if dist > threshold:
                continue
            if dist < best_dist or (
                dist == best_dist
                and str(raw.get("text_preview_hash") or "") == fp
            ):
                best_dist = dist
                best = self._to_entry(raw)
        return best

    def register(
        self,
        text: str,
        parent_id: str,
        source: str,
        *,
        department: str,
    ) -> ChunkDedupEntry:
        entry = ChunkDedupEntry(
            simhash=simhash64(text),
            parent_id=parent_id,
            canonical_source=source,
            department=department,
            text_preview_hash=preview_fingerprint(text),
        )
        with _lock:
            self._entries.append(
                {
                    "simhash": entry.simhash,
                    "parent_id": entry.parent_id,
                    "canonical_source": entry.canonical_source,
                    "alias_sources": [],
                    "department": entry.department,
                    "text_preview_hash": entry.text_preview_hash,
                }
            )
            self._save()
        return entry

    def add_alias(self, parent_id: str, alias_source: str) -> None:
        with _lock:
            for raw in self._entries:
                if str(raw.get("parent_id") or "") != parent_id:
                    continue
                aliases = list(raw.get("alias_sources") or [])
                if alias_source not in aliases and alias_source != raw.get("canonical_source"):
                    aliases.append(alias_source)
                raw["alias_sources"] = aliases
                break
            self._save()

    def remove_by_source(self, source: str) -> None:
        with _lock:
            kept: list[dict[str, Any]] = []
            for raw in self._entries:
                canonical = str(raw.get("canonical_source") or "")
                aliases = list(raw.get("alias_sources") or [])
                if canonical == source:
                    if aliases:
                        raw["canonical_source"] = aliases.pop(0)
                        raw["alias_sources"] = aliases
                        kept.append(raw)
                    continue
                if source in aliases:
                    raw["alias_sources"] = [a for a in aliases if a != source]
                kept.append(raw)
            self._entries = kept
            self._save()

    def aliases_for_parent(self, parent_id: str) -> list[str]:
        for raw in self._entries:
            if str(raw.get("parent_id") or "") == parent_id:
                return list(raw.get("alias_sources") or [])
        return []


_store: ChunkDedupStore | None = None


def get_chunk_dedup_store() -> ChunkDedupStore:
    global _store
    if _store is None:
        _store = ChunkDedupStore()
    return _store


def reset_chunk_dedup_store() -> None:
    global _store
    _store = None
