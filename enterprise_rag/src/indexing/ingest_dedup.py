"""Orchestrate L1 document + L2 parent-chunk dedup during ingest."""

from __future__ import annotations

from dataclasses import dataclass, field

from chunker.parent_child import ChildChunk, ParentChunk
from config import settings
from indexing.chunk_dedup_store import get_chunk_dedup_store
from indexing.dedup_text import content_hash
from indexing.document_registry import DocRecord, get_document_registry


@dataclass
class IngestDedupStats:
    content_hash: str = ""
    doc_duplicate: bool = False
    canonical_source: str | None = None
    alias_sources: list[str] = field(default_factory=list)
    skipped_parents: int = 0
    skipped_children: int = 0
    indexed_parents: int = 0
    indexed_children: int = 0
    message: str | None = None


@dataclass
class IngestDedupPlan:
    """Outcome of dedup planning before embedding."""

    early_exit: bool = False
    parents: list[ParentChunk] = field(default_factory=list)
    children: list[ChildChunk] = field(default_factory=list)
    stats: IngestDedupStats = field(default_factory=IngestDedupStats)


def check_document_duplicate(text: str, source: str) -> IngestDedupPlan | None:
    """
    L1: same content_hash from a different source → alias only, skip embed/index.
    Returns a plan with early_exit=True, or None to continue ingest.
    """
    if not settings.ingest_content_hash_enabled:
        return None

    registry = get_document_registry()
    digest = content_hash(text)
    existing = registry.lookup_by_hash(digest)

    if existing is None:
        return None

    canonical = existing.canonical_source
    if source == canonical or source in existing.alias_sources:
        return None

    registry.add_alias(canonical, source, digest)
    stats = IngestDedupStats(
        content_hash=digest,
        doc_duplicate=True,
        canonical_source=canonical,
        alias_sources=list(existing.alias_sources) + [source],
        message=(
            f"文档内容与「{canonical}」相同（content_hash 命中），"
            f"已登记别名「{source}」，跳过重复嵌入与索引。"
        ),
    )
    return IngestDedupPlan(early_exit=True, stats=stats)


def filter_parent_child_duplicates(
    parents: list[ParentChunk],
    children: list[ChildChunk],
    source: str,
    *,
    doc_content_hash: str | None = None,
) -> IngestDedupPlan:
    """L2: drop parent/child groups that near-duplicate an existing indexed parent."""
    stats = IngestDedupStats(content_hash=doc_content_hash or "")
    if not settings.ingest_chunk_dedup_enabled:
        stats.indexed_parents = len(parents)
        stats.indexed_children = len(children)
        return IngestDedupPlan(parents=parents, children=children, stats=stats)

    store = get_chunk_dedup_store()
    kept_parents: list[ParentChunk] = []
    kept_children: list[ChildChunk] = []
    skipped_pids: set[str] = set()

    for parent in parents:
        dup = store.find_near_duplicate(parent.text, department=parent.department)
        if dup and dup.parent_id:
            store.add_alias(dup.parent_id, source)
            skipped_pids.add(parent.parent_id)
            stats.skipped_parents += 1
            continue
        store.register(parent.text, parent.parent_id, source, department=parent.department)
        kept_parents.append(parent)

    for child in children:
        if child.parent_id in skipped_pids:
            stats.skipped_children += 1
            continue
        kept_children.append(child)

    stats.indexed_parents = len(kept_parents)
    stats.indexed_children = len(kept_children)
    if stats.skipped_parents or stats.skipped_children:
        stats.message = (
            f"块级去重：跳过 {stats.skipped_parents} 个父块、"
            f"{stats.skipped_children} 个子块（与已有索引近似重复）。"
        )
    return IngestDedupPlan(parents=kept_parents, children=kept_children, stats=stats)


def prepare_source_reingest(source: str) -> None:
    """Purge L2 entries owned by source before re-indexing same filename."""
    if settings.ingest_chunk_dedup_enabled:
        get_chunk_dedup_store().remove_by_source(source)


def finalize_document_registry(
    source: str,
    text: str,
    *,
    parent_count: int,
    child_count: int,
) -> DocRecord | None:
    if not settings.ingest_content_hash_enabled:
        return None
    digest = content_hash(text)
    registry = get_document_registry()
    registry.register(
        source,
        digest,
        parent_count=parent_count,
        child_count=child_count,
    )
    return registry.lookup_by_hash(digest)
