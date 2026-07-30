"""Reclassify English exam questions using 第X部分 section detection.

Fixes legacy rows where listening/reading/cloze were stored as ``choice``.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from exam_bank import store  # noqa: E402
from exam_bank.item_split import split_items_rules  # noqa: E402
from exam_bank.store import _connect, _lock, init_exam_bank_db, update_question  # noqa: E402

_WRITING_RE = re.compile(
    r"词数|续写|书面表达|Dear\s|假定你是|邀请他参加|活动流程|活动时间|开头和结尾|你的观点|你的设想"
)
_FILL_RE = re.compile(r"空白处填|语法填空|填入\s*\d+\s*个适当")
_INSTR_RE = re.compile(
    r"答卷前|考生务必|回答选择题时|考试结束后|请按如下格式|选择题必须使用|非选择题必须"
)


def _stem_key(stem: str) -> str:
    s = re.sub(r"\s+", " ", (stem or "").strip().lower())
    # keep latin words for matching dual-column debris
    letters = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in s)
    return re.sub(r"\s+", " ", letters).strip()[:80]


def _heuristic_qtype(stem: str) -> str | None:
    if _INSTR_RE.search(stem or ""):
        return None
    if _WRITING_RE.search(stem or ""):
        return "writing"
    if _FILL_RE.search(stem or ""):
        return "fill"
    return None


def _pick_qtype_for_question(q: dict, items_by_no: dict[str, list[dict]]) -> str | None:
    stem = str(q.get("stem") or "")
    forced = _heuristic_qtype(stem)
    if forced:
        return forced
    qno = str(q.get("question_no") or "").strip()
    cands = items_by_no.get(qno) or []
    if not cands:
        return None
    key = _stem_key(stem)
    best = None
    best_score = -1
    for it in cands:
        it_stem = str(it.get("stem") or "")
        it_key = _stem_key(it_stem)
        score = 0
        if key and it_key and (key in it_key or it_key in key):
            score += 10
        if key and it_key:
            aw = set(key.split())
            bw = set(it_key.split())
            score += len(aw & bw)
        if it.get("options"):
            score += 2
        if score > best_score:
            best_score = score
            best = it
    if best is None:
        return None
    # Avoid applying a random same-number item when stems share nothing
    if best_score <= 0 and stem.strip():
        # fallback: prefer English-like candidate for choice-like rows
        for it in cands:
            if re.search(r"[A-Za-z]{4,}", str(it.get("stem") or "")):
                return str(it.get("qtype") or "other")
        return None
    return str(best.get("qtype") or "other")


def main() -> int:
    init_exam_bank_db()
    with _lock:
        conn = _connect()
        try:
            papers = conn.execute(
                """
                SELECT sp.id, sp.raw_text, sp.collection_id
                FROM source_papers sp
                JOIN collections c ON c.id = sp.collection_id
                WHERE c.subject = '英语'
                """
            ).fetchall()
        finally:
            conn.close()

    updated = 0
    for p in papers:
        items = split_items_rules(p["raw_text"] or "", subject="英语")
        by_no: dict[str, list[dict]] = {}
        for it in items:
            qno = str(it.get("question_no") or "").strip()
            if not qno:
                continue
            by_no.setdefault(qno, []).append(it)

        qs, _ = store.list_questions(
            collection_id=p["collection_id"], status=None, limit=10000
        )
        for q in qs:
            if (q.get("source_paper_id") or "") != p["id"]:
                continue
            new_qt = _pick_qtype_for_question(q, by_no)
            if not new_qt or new_qt == q.get("qtype"):
                continue
            update_question(q["id"], qtype=new_qt)
            updated += 1
            stem = (q.get("stem") or "")[:48].replace("\n", " ")
            print(f"{q.get('question_no')}: {q.get('qtype')} -> {new_qt} | {stem}")

    print("updated", updated)
    for c in store.list_collections(apply_acl=False):
        if c.get("subject") != "英语":
            continue
        items, _ = store.list_questions(collection_id=c["id"], status=None, limit=10000)
        print(c.get("name"), Counter(q.get("qtype") for q in items), "n=", len(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
