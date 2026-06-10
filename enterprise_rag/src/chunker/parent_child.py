from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # 旧环境：仅 community 暴露该符号
    from langchain_community.text_splitters import RecursiveCharacterTextSplitter  # type: ignore[no-redef]

from chunker.utils import new_chunk_id, normalize_ingest_tags
from config import settings


@dataclass
class ChildChunk:
    chunk_id: str
    parent_id: str
    text: str
    source: str
    department: str
    permission_label: str
    child_index: int
    tags: list[str]


@dataclass
class ParentChunk:
    parent_id: str
    text: str
    source: str
    department: str
    permission_label: str
    order: int
    tags: list[str]


def split_parent_child(
    text: str,
    source: str,
    department: str | None = None,
    permission_label: str | None = None,
    tags: list[str] | None = None,
) -> tuple[list[ParentChunk], list[ChildChunk]]:
    """步骤2：父子块 + 元数据（部门、权限标签、自定义标签）。"""
    dept = department or settings.default_department
    perm = permission_label or settings.default_permission_label
    doc_tags = normalize_ingest_tags(tags)

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.parent_chunk_size,
        chunk_overlap=settings.parent_chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.child_chunk_size,
        chunk_overlap=settings.child_chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
    )

    parent_texts = parent_splitter.split_text(text)
    parents: list[ParentChunk] = []
    children: list[ChildChunk] = []

    for p_order, p_text in enumerate(parent_texts):
        pid = new_chunk_id("p")
        parents.append(
            ParentChunk(
                parent_id=pid,
                text=p_text,
                source=source,
                department=dept,
                permission_label=perm,
                order=p_order,
                tags=list(doc_tags),
            )
        )
        for c_order, c_text in enumerate(child_splitter.split_text(p_text)):
            cid = new_chunk_id("c")
            children.append(
                ChildChunk(
                    chunk_id=cid,
                    parent_id=pid,
                    text=c_text,
                    source=source,
                    department=dept,
                    permission_label=perm,
                    child_index=c_order,
                    tags=list(doc_tags),
                )
            )
    return parents, children


def persist_chunks_jsonl(
    parents: list[ParentChunk],
    children: list[ChildChunk],
    out_dir: Path | None = None,
) -> Path:
    out_dir = out_dir or settings.data_chunks_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"chunks_{uuid.uuid4().hex[:12]}.jsonl"
    path = out_dir / name
    with path.open("w", encoding="utf-8") as f:
        for p in parents:
            f.write(json.dumps({"type": "parent", **asdict(p)}, ensure_ascii=False) + "\n")
        for c in children:
            f.write(json.dumps({"type": "child", **asdict(c)}, ensure_ascii=False) + "\n")
    return path


def iter_child_chunks_for_indexing(
    text: str,
    source: str,
    department: str | None = None,
    permission_label: str | None = None,
    tags: list[str] | None = None,
) -> Iterator[ChildChunk]:
    _, children = split_parent_child(text, source, department, permission_label, tags=tags)
    yield from children
