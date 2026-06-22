#!/usr/bin/env python3
"""Rebuild domain_lexicon.json from data/raw (and optional chunk jsonl)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
sys.path.insert(0, str(SRC))


def _collect_chunk_sources(chunks_dir: Path) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    if not chunks_dir.is_dir():
        return sources
    for path in sorted(chunks_dir.glob("*.jsonl")):
        parents: dict[str, str] = {}
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("type") == "parent":
                    pid = str(row.get("parent_id") or "")
                    parents[pid] = str(row.get("text") or "")
                elif row.get("type") == "child":
                    pid = str(row.get("parent_id") or "")
                    text = str(row.get("text") or "")
                    src = str(row.get("source") or path.name)
                    key = f"{src}#{pid or row.get('chunk_id', '')}"
                    prev = parents.get(pid, "")
                    merged = (prev + "\n" + text).strip() if prev else text
                    if merged:
                        sources.append((key, merged))
        except (OSError, json.JSONDecodeError):
            continue
    return sources


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild domain lexicon from corpus files")
    parser.add_argument("--raw-dir", type=Path, default=None, help="Override data/raw directory")
    parser.add_argument("--chunks-dir", type=Path, default=None, help="Also scan chunk jsonl directory")
    parser.add_argument("--replace", action="store_true", help="Replace lexicon instead of merging")
    parser.add_argument("--max-terms", type=int, default=80, help="Max terms per document")
    args = parser.parse_args()

    from config import settings
    from retrieval.domain_lexicon import (
        rebuild_domain_lexicon_from_raw_dir,
        rebuild_domain_lexicon_from_texts,
    )

    raw_stats = rebuild_domain_lexicon_from_raw_dir(
        args.raw_dir,
        replace=args.replace,
        max_terms_per_doc=args.max_terms,
    )
    chunk_stats = {"term_count": raw_stats.get("term_count", 0), "ingested_rows": 0}
    chunks_dir = args.chunks_dir or settings.data_chunks_dir
    chunk_sources = _collect_chunk_sources(Path(chunks_dir))
    if chunk_sources:
        chunk_stats = rebuild_domain_lexicon_from_texts(
            chunk_sources,
            max_terms_per_doc=args.max_terms,
            replace=False,
        )
    print(
        json.dumps(
            {
                "raw": raw_stats,
                "chunks": chunk_stats,
                "lexicon_path": str(settings.domain_lexicon_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
