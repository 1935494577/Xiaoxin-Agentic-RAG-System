#!/usr/bin/env python3
"""Ingest gold gaokao math papers (fixtures + optional live DOCX) into exam bank.

Usage (from repo root):
  set PYTHONPATH=enterprise_rag/src
  python scripts/ingest_gold_exam_papers.py

Uses rules split (use_llm=False) so CI / offline works. Prefers source DOCX when
manifest.path exists for [[EQ]] extraction; otherwise uses fixture .txt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
sys.path.insert(0, str(SRC))

FIXTURES = ROOT / "tests" / "fixtures" / "exam_papers"
MANIFEST = FIXTURES / "manifest.json"


def main() -> int:
    from exam_bank import store
    from exam_bank.docx_extract import default_exam_media_root, extract_docx_exam
    from exam_bank.item_split import parse_paper_items

    store.init_exam_bank_db()
    meta = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cols = store.list_collections()
    col = next(
        (
            c
            for c in cols
            if c.get("region") == "浙江"
            and c.get("subject") == "数学"
            and c.get("grade") == "高三"
        ),
        None,
    )
    if not col:
        col = store.create_collection(
            name="浙江·数学·高三",
            subject="数学",
            grade="高三",
            region="浙江",
            description="金标样卷（新课标数学）",
        )
    print(f"collection={col['id']} {col.get('name')}")

    failed = 0
    for row in meta:
        year = str(row.get("year") or "")
        kind = str(row.get("kind") or "other")
        if kind not in {"answer", "blank"}:
            continue
        text = ""
        media: list = []
        src_path = Path(row.get("path") or "")
        fname = str(row.get("name") or row.get("file") or "")
        if src_path.is_file() and src_path.suffix.lower() == ".docx":
            extracted = extract_docx_exam(src_path, media_dir=default_exam_media_root())
            text = extracted["text"]
            media = extracted.get("media") or []
            print(f"[extract] {fname} eq={extracted.get('eq_count')} chars={len(text)}")
        else:
            fix = FIXTURES / str(row.get("file") or "")
            if not fix.is_file():
                print(f"[skip] missing fixture {row}")
                failed += 1
                continue
            text = fix.read_text(encoding="utf-8")
            print(f"[fixture] {fix.name} chars={len(text)}")

        parsed = parse_paper_items(
            text,
            subject="数学",
            grade="高三",
            region="浙江",
            stage="senior",
            use_llm=False,
            clean=True,
        )
        items = list(parsed.get("items") or [])
        n = len(items)
        choice_ok = sum(
            1
            for it in items
            if it.get("qtype") in {"choice", "multi"} and len(it.get("options") or []) >= 4
        )
        with_ans = sum(1 for it in items if (it.get("answer") or "").strip())
        print(
            f"  split n={n} choice4+={choice_ok} answers={with_ans} "
            f"embedded={parsed.get('answers_embedded')} media={len(media)}"
        )
        if n < 15:
            print("  FAIL expected >=15 items")
            failed += 1
            continue

        created_ids: list[str] = []
        for it in items:
            if not it.get("selected", True):
                continue
            q = store.create_question(
                collection_id=col["id"],
                qtype=str(it.get("qtype") or "other"),
                stem=str(it.get("stem") or ""),
                options=list(it.get("options") or []),
                answer=str(it.get("answer") or ""),
                analysis=str(it.get("analysis") or ""),
                knowledge_tags=list(it.get("knowledge_tags") or []),
                region="浙江",
                year=year,
                quality_status="published",
                question_no=str(it.get("question_no") or ""),
                difficulty=int(it.get("difficulty") or 3),
            )
            created_ids.append(q["id"])
        sp = store.create_source_paper(
            collection_id=col["id"],
            title=f"{year} {kind} {fname}"[:120],
            raw_text=text,
            source_filename=fname,
            question_ids=created_ids,
        )
        for qid in created_ids:
            store.update_question(qid, source_paper_id=sp["id"])
        print(f"  committed {len(created_ids)} paper={sp['id']}")

    if failed:
        print(f"DONE with {failed} failures")
        return 1
    print("DONE ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
