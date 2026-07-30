#!/usr/bin/env python3
"""Batch-ingest all papers under d:\\试卷资料\\试卷资料 into exam bank.

- Infer region / grade / subject / year / exam_type from path
- Dedupe (prefer 解析版 + docx + A4)
- One collection per 地区·学科·年级
- Questions tagged with exam_type (chapter) + year/region for secondary filters

Usage (repo root):
  set PYTHONPATH=enterprise_rag/src
  python scripts/ingest_all_exam_papers.py
  python scripts/ingest_all_exam_papers.py --root "d:\\试卷资料\\试卷资料"
  python scripts/ingest_all_exam_papers.py --no-llm   # 仅规则拆题（不推荐灌生产库）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "enterprise_rag" / "src"
sys.path.insert(0, str(SRC))

DEFAULT_CORPUS = Path(r"d:\试卷资料\试卷资料")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch-ingest exam corpus into exam bank (LLM split by default)"
    )
    parser.add_argument("--root", type=str, default=str(DEFAULT_CORPUS))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="0=all")
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Clear exam bank (+ optional media) before ingest so formula extract is rebuilt",
    )
    parser.add_argument(
        "--purge-media",
        action="store_true",
        help="Also delete exam_media folders (use with --purge)",
    )
    parser.add_argument(
        "--structure",
        action="store_true",
        help="Use PP-StructureV3+FormulaNet(+LLM) for PDF/图片 so stems keep $LaTeX$",
    )
    parser.add_argument(
        "--no-structure-llm",
        action="store_true",
        help="Structure OCR only; item split uses --no-llm / default LLM separately",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Rule split only (skip DeepSeek item extract). Default is LLM-first.",
    )
    return parser


def resolve_use_llm(args: argparse.Namespace) -> bool:
    """Batch ingest defaults to LLM; --no-llm opts out."""
    return not bool(getattr(args, "no_llm", False))


def _load_text(path: Path) -> tuple[str, list, str]:
    from exam_bank.docx_extract import default_exam_media_root, extract_docx_exam

    suf = path.suffix.lower()
    if suf == ".docx":
        extracted = extract_docx_exam(path, media_dir=default_exam_media_root())
        return (
            str(extracted.get("text") or ""),
            list(extracted.get("media") or []),
            str(extracted.get("ingest_id") or ""),
        )
    if suf in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore"), [], ""
    if suf == ".pdf":
        try:
            import pdfplumber

            parts: list[str] = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
            return "\n".join(parts), [], ""
        except Exception as e:
            raise RuntimeError(f"pdf_load_failed:{e}") from e
    # legacy .doc — best-effort
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "doc_parser", SRC / "document_loader" / "parser.py"
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return str(mod.load_document_text(path) or ""), [], ""
    except Exception as e:
        raise RuntimeError(f"load_failed:{e}") from e


def _load_via_structure(
    path: Path,
    *,
    subject: str,
    grade: str,
    use_llm: bool = True,
) -> tuple[str, list[dict], str, str]:
    """PP-StructureV3 + LaTeXOCR (+ optional DeepSeek) → text + items.

    Returns (reading_text, items, media_ingest_id, engine).
    """
    from exam_bank.paper_structure_parse import parse_exam_paper

    result = parse_exam_paper(
        path,
        use_llm=use_llm,
        subject=subject,
        grade=grade,
    )
    if not result.get("ok"):
        raise RuntimeError(result.get("message") or result.get("error") or "structure_failed")
    text = str(result.get("reading_order_text") or "")
    items: list[dict] = []
    for q in result.get("questions") or []:
        stem = str(q.get("stem") or "").strip()
        if not stem:
            continue
        items.append(
            {
                "question_no": str(q.get("question_no") or ""),
                "qtype": str(q.get("qtype") or "other"),
                "stem": stem,
                "options": list(q.get("options") or []),
                "answer": str(q.get("answer") or ""),
                "analysis": str(q.get("analysis") or ""),
                "knowledge_tags": list(q.get("knowledge_tags") or []),
                "chapter": str(q.get("chapter") or ""),
                "difficulty": int(q.get("difficulty") or 3),
                "selected": True,
            }
        )
    engine = str(result.get("engine") or "pp-structurev3")
    # DOCX structure path may still leave [[EQ]] — keep empty media id (images not linked)
    return text, items, "", engine


def _already_ingested_filenames(store) -> set[str]:
    from exam_bank.store import _connect, _lock

    names: set[str] = set()
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT source_filename FROM source_papers WHERE source_filename != ''"
            ).fetchall()
        finally:
            conn.close()
    for r in rows:
        names.add(str(r[0] if not hasattr(r, "keys") else r["source_filename"]))
    return names


def _get_or_create_collection(store, *, region: str, subject: str, grade: str):
    cols = store.list_collections()
    for c in cols:
        if (
            c.get("region") == region
            and c.get("subject") == subject
            and c.get("grade") == grade
        ):
            return c
    return store.create_collection(
        name=f"{region}·{subject}·{grade}",
        subject=subject,
        grade=grade,
        region=region,
        description="试卷资料库自动建库",
        visibility="tenant_shared",
    )


def main() -> int:
    args = build_arg_parser().parse_args()
    use_llm = resolve_use_llm(args)

    from exam_bank import store
    from exam_bank.corpus_meta import select_corpus_files
    from exam_bank.item_split import parse_paper_items
    from exam_bank.docx_extract import default_exam_media_root

    root = Path(args.root)
    if not root.is_dir():
        print(f"missing corpus root: {root}")
        return 1

    store.init_exam_bank_db()
    if args.purge:
        stats = store.purge_exam_bank()
        print(f"purged bank: {stats}")
        if args.purge_media:
            import shutil

            media = default_exam_media_root()
            if media.is_dir():
                shutil.rmtree(media, ignore_errors=True)
                print(f"removed media root: {media}")
            media.mkdir(parents=True, exist_ok=True)
    selected = select_corpus_files(root)
    if args.limit and args.limit > 0:
        selected = selected[: args.limit]
    # DOCX first (fast python-docx / EQ media); PDF structure is CPU-heavy
    selected = sorted(
        selected,
        key=lambda m: 0 if Path(m["path"]).suffix.lower() == ".docx" else 1,
    )
    seen = _already_ingested_filenames(store)
    print(
        f"selected {len(selected)} papers after dedupe (from {root}); "
        f"already={len(seen)}; structure={args.structure}; use_llm={use_llm}"
    )

    ok = 0
    failed = 0
    skipped = 0
    questions_total = 0
    collections_touched: set[str] = set()

    for i, meta in enumerate(selected, 1):
        path = Path(meta["path"])
        region = meta["region"]
        subject = meta["subject"]
        grade = meta["grade"]
        year = meta["year"]
        exam_type = meta["exam_type"]
        paper_kind = meta["paper_kind"]
        print(
            f"[{i}/{len(selected)}] {year} {region} {grade} {subject} {exam_type} "
            f"({paper_kind}) {path.name}"
        )
        if path.name in seen:
            print("  SKIP already ingested filename")
            skipped += 1
            continue
        if args.dry_run:
            ok += 1
            continue

        text = ""
        media: list = []
        ingest_id = ""
        items: list = []
        used_structure = False

        suf = path.suffix.lower()
        if args.structure and suf in {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}:
            try:
                text, items, ingest_id, eng = _load_via_structure(
                    path,
                    subject=subject if subject != "未知" else "",
                    grade=grade if grade != "未分年级" else "",
                    use_llm=not args.no_structure_llm,
                )
                used_structure = True
                print(f"  structure engine={eng} llm_items={len(items)}")
            except Exception as e:
                print(f"  structure FAIL → fallback: {e}")
        # DOCX: keep [[EQ:n]] + media (MathType); Structure OCR is for PDF/scans → $LaTeX$

        if not used_structure or (used_structure and len(items) < 3 and not (text or "").strip()):
            try:
                text, media, ingest_id = _load_text(path)
            except Exception as e:
                print(f"  SKIP load: {e}")
                skipped += 1
                continue
            if not (text or "").strip():
                print("  SKIP empty text")
                skipped += 1
                continue
            try:
                parsed = parse_paper_items(
                    text,
                    subject=subject if subject != "未知" else "",
                    grade=grade if grade != "未分年级" else "",
                    region=region if region != "未知" else "",
                    stage=str(meta.get("stage") or ""),
                    use_llm=use_llm,
                    clean=True,
                )
            except Exception as e:
                print(f"  FAIL parse: {e}")
                failed += 1
                continue
            if use_llm and (parsed.get("error") or parsed.get("router") == "llm_failed"):
                print(
                    f"  FAIL llm_split: {parsed.get('message') or parsed.get('error')}"
                )
                failed += 1
                continue
            items = list(parsed.get("items") or [])
            print(f"  split router={parsed.get('router') or '-'} items={len(items)}")
        elif used_structure and len(items) < 3 and (text or "").strip():
            # Structure OCR ok but structure-LLM empty → item split (LLM default)
            try:
                parsed = parse_paper_items(
                    text,
                    subject=subject if subject != "未知" else "",
                    grade=grade if grade != "未分年级" else "",
                    region=region if region != "未知" else "",
                    stage=str(meta.get("stage") or ""),
                    use_llm=use_llm,
                    clean=True,
                )
                if use_llm and (parsed.get("error") or parsed.get("router") == "llm_failed"):
                    print(
                        f"  FAIL llm_split after structure: "
                        f"{parsed.get('message') or parsed.get('error')}"
                    )
                    failed += 1
                    continue
                items = list(parsed.get("items") or [])
                print(
                    f"  structure text → split router={parsed.get('router') or '-'} "
                    f"items={len(items)}"
                )
            except Exception as e:
                print(f"  FAIL parse after structure: {e}")
                failed += 1
                continue

        if len(items) < 3:
            print(f"  SKIP too_few_items={len(items)}")
            skipped += 1
            continue
        try:
            col = _get_or_create_collection(
                store, region=region, subject=subject, grade=grade
            )
        except Exception as e:
            print(f"  FAIL collection: {e}")
            failed += 1
            continue
        collections_touched.add(col["id"])
        tags_base = [exam_type, f"卷种:{paper_kind}"]
        if year:
            tags_base.append(f"年份:{year}")
        track = str(meta.get("track") or "")
        if track:
            tags_base.append(f"文理:{track}")
        if used_structure:
            tags_base.append("解析:structure")
        created_ids: list[str] = []
        for it in items:
            if not it.get("selected", True):
                continue
            tags = list(it.get("knowledge_tags") or [])
            for t in tags_base:
                if t and t not in tags:
                    tags.append(t)
            q = store.create_question(
                collection_id=col["id"],
                qtype=str(it.get("qtype") or "other"),
                stem=str(it.get("stem") or ""),
                options=list(it.get("options") or []),
                answer=str(it.get("answer") or ""),
                analysis=str(it.get("analysis") or ""),
                knowledge_tags=tags,
                region=region if region != "未知" else "",
                year=year,
                subject=subject if subject != "未知" else "",
                grade=grade if grade != "未分年级" else "",
                chapter=str(it.get("chapter") or exam_type or ""),
                quality_status="published",
                question_no=str(it.get("question_no") or ""),
                difficulty=int(it.get("difficulty") or 3),
                media_ingest_id=ingest_id,
            )
            created_ids.append(q["id"])
        sp = store.create_source_paper(
            collection_id=col["id"],
            title=f"{year} {exam_type} {path.name}"[:160],
            raw_text=text,
            source_filename=path.name,
            question_ids=created_ids,
            media_ingest_id=ingest_id,
        )
        for qid in created_ids:
            store.update_question(qid, source_paper_id=sp["id"])
        questions_total += len(created_ids)
        ok += 1
        print(
            f"  OK items={len(created_ids)} answers={sum(1 for it in items if it.get('answer'))} "
            f"eq_media={len(media)} ingest={ingest_id or '-'} structure={used_structure} → {col.get('name')}"
        )

    print(
        f"DONE ok={ok} skipped={skipped} failed={failed} "
        f"questions={questions_total} collections={len(collections_touched)}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
