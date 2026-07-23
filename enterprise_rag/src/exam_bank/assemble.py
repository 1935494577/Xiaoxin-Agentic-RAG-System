"""Rule-based paper assembly (deterministic with seed)."""

from __future__ import annotations

import random
from typing import Any

from exam_bank import store
from exam_bank.subject_catalog import (
    DIFFICULTY_BANDS,
    DIFFICULTY_BAND_LABELS,
    normalize_qtype,
    qtype_label,
)
from exam_bank.types import DEFAULT_TENANT


def _stable_shuffle(items: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    rng = random.Random(int(seed))
    out = list(items)
    rng.shuffle(out)
    return out


def _band_of(difficulty: int) -> str:
    d = int(difficulty)
    for band, (lo, hi) in DIFFICULTY_BANDS.items():
        if lo <= d <= hi:
            return band
    return "mid"


def _filter_pool(
    questions: list[dict[str, Any]],
    *,
    difficulty_min: int | None,
    difficulty_max: int | None,
    knowledge_tags_any: list[str] | None,
) -> list[dict[str, Any]]:
    out = []
    tags_any = [t for t in (knowledge_tags_any or []) if t]
    for q in questions:
        d = int(q.get("difficulty") or 0)
        if difficulty_min is not None and d < difficulty_min:
            continue
        if difficulty_max is not None and d > difficulty_max:
            continue
        if tags_any:
            qtags = set(q.get("knowledge_tags") or [])
            if not qtags.intersection(tags_any):
                continue
        out.append(q)
    return out


def render_markdown(
    *,
    title: str,
    ordered: list[dict[str, Any]],
    include_answers: bool,
) -> str:
    lines = [f"# {title}", ""]
    by_type: dict[str, list[dict[str, Any]]] = {}
    order_keys: list[str] = []
    for q in ordered:
        qt = str(q.get("qtype") or "other")
        if qt not in by_type:
            order_keys.append(qt)
            by_type[qt] = []
        by_type[qt].append(q)

    n = 1
    for qt in order_keys:
        group = by_type.get(qt) or []
        if not group:
            continue
        lines.append(f"## {qtype_label(qt)}")
        lines.append("")
        for q in group:
            lines.append(f"**{n}.** {q.get('stem') or ''}")
            opts = q.get("options") or []
            for opt in opts:
                lines.append(f"- {opt}")
            lines.append("")
            n += 1

    if include_answers:
        lines.append("---")
        lines.append("")
        lines.append("## 答案与解析")
        lines.append("")
        n = 1
        for q in ordered:
            lines.append(f"**{n}.** 答案：{q.get('answer') or '（略）'}")
            analysis = (q.get("analysis") or "").strip()
            if analysis:
                lines.append(f"解析：{analysis}")
            lines.append("")
            n += 1

    return "\n".join(lines).rstrip() + "\n"


def _pick_for_qtype(
    group: list[dict[str, Any]],
    need_n: int,
    *,
    seed: int,
    qt: str,
    remaining_bands: dict[str, int] | None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Return list of questions or an error dict."""
    if not group:
        label = qtype_label(qt)
        return {
            "ok": False,
            "error": "missing_qtype",
            "detail": {
                "qtype": qt,
                "label": label,
                "message": f"没有相应题型：{label}",
            },
        }
    group = _stable_shuffle(group, seed ^ (sum(ord(c) for c in str(qt)) & 0xFFFF))
    picked: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    if remaining_bands:
        for band, want in list(remaining_bands.items()):
            if want <= 0 or len(picked) >= need_n:
                continue
            lo, hi = DIFFICULTY_BANDS[band]
            cand = [
                q
                for q in group
                if q["id"] not in used_ids and lo <= int(q.get("difficulty") or 0) <= hi
            ]
            take = min(want, need_n - len(picked), len(cand))
            for q in cand[:take]:
                picked.append(q)
                used_ids.add(q["id"])
                remaining_bands[band] = remaining_bands.get(band, 0) - 1

    for q in group:
        if len(picked) >= need_n:
            break
        if q["id"] in used_ids:
            continue
        picked.append(q)
        used_ids.add(q["id"])
        if remaining_bands is not None:
            b = _band_of(int(q.get("difficulty") or 3))
            if b in remaining_bands:
                remaining_bands[b] = remaining_bands.get(b, 0) - 1

    if len(picked) < need_n:
        return {
            "ok": False,
            "error": "insufficient_questions",
            "detail": {
                "qtype": qt,
                "label": qtype_label(qt),
                "need": need_n,
                "have": len(group),
                "message": f"题型「{qtype_label(qt)}」数量不足：需要 {need_n}，仅有 {len(group)}",
            },
        }
    return picked[:need_n]


def assemble_paper(
    *,
    collection_id: str,
    title: str,
    spec: dict[str, Any] | None = None,
    include_answers: bool = True,
    tenant_id: str = DEFAULT_TENANT,
) -> dict[str, Any]:
    spec = dict(spec or {})
    raw_by = spec.get("by_qtype") or {}
    if not isinstance(raw_by, dict) or not raw_by:
        return {"ok": False, "error": "invalid_spec", "detail": {"reason": "by_qtype required"}}

    by_qtype: dict[str, int] = {}
    for k, v in raw_by.items():
        qt = normalize_qtype(str(k))
        by_qtype[qt] = by_qtype.get(qt, 0) + int(v)

    dmin = spec.get("difficulty_min")
    dmax = spec.get("difficulty_max")
    tags_any = spec.get("knowledge_tags_any")
    if tags_any is not None and not isinstance(tags_any, list):
        tags_any = []
    seed = int(spec.get("seed") if spec.get("seed") is not None else 0)

    raw_bands = spec.get("by_difficulty_band") or {}
    remaining_bands: dict[str, int] | None = None
    if isinstance(raw_bands, dict) and raw_bands:
        remaining_bands = {
            str(k): int(v)
            for k, v in raw_bands.items()
            if str(k) in DIFFICULTY_BANDS and int(v) > 0
        }
        if remaining_bands:
            # Pre-check band availability in pool (all published)
            pool_all, _ = store.list_questions(
                collection_id=collection_id, status="published", limit=500, offset=0
            )
            pool_all = _filter_pool(
                pool_all,
                difficulty_min=int(dmin) if dmin is not None else None,
                difficulty_max=int(dmax) if dmax is not None else None,
                knowledge_tags_any=[str(x) for x in (tags_any or [])],
            )
            # Restrict to requested qtypes
            wanted = set(by_qtype)
            pool_all = [q for q in pool_all if normalize_qtype(str(q.get("qtype"))) in wanted]
            for band, need in remaining_bands.items():
                lo, hi = DIFFICULTY_BANDS[band]
                have = sum(1 for q in pool_all if lo <= int(q.get("difficulty") or 0) <= hi)
                if have < need:
                    return {
                        "ok": False,
                        "error": "insufficient_difficulty",
                        "detail": {
                            "band": band,
                            "label": DIFFICULTY_BAND_LABELS.get(band, band),
                            "need": need,
                            "have": have,
                            "message": (
                                f"没有足够的「{DIFFICULTY_BAND_LABELS.get(band, band)}」难度题目："
                                f"需要 {need}，仅有 {have}"
                            ),
                        },
                    }
            remaining_bands = dict(remaining_bands)

    pool, _ = store.list_questions(
        collection_id=collection_id,
        status="published",
        limit=500,
        offset=0,
    )
    pool = _filter_pool(
        pool,
        difficulty_min=int(dmin) if dmin is not None else None,
        difficulty_max=int(dmax) if dmax is not None else None,
        knowledge_tags_any=[str(x) for x in (tags_any or [])],
    )

    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for qt, need_n in by_qtype.items():
        if need_n <= 0:
            continue
        group = [q for q in pool if normalize_qtype(str(q.get("qtype"))) == qt]
        result = _pick_for_qtype(
            group,
            need_n,
            seed=seed,
            qt=qt,
            remaining_bands=remaining_bands,
        )
        if isinstance(result, dict) and result.get("ok") is False:
            return result
        assert isinstance(result, list)
        selected.extend(result)
        counts[qt] = need_n

    md = render_markdown(title=title or "未命名试卷", ordered=selected, include_answers=include_answers)
    qids = [str(q["id"]) for q in selected]
    paper = store.save_paper(
        collection_id=collection_id,
        title=title or "未命名试卷",
        spec=spec,
        question_ids=qids,
        markdown=md,
        tenant_id=tenant_id,
    )
    return {
        "ok": True,
        "paper_id": paper["id"],
        "title": paper["title"],
        "question_ids": qids,
        "counts": counts,
        "markdown": md,
    }
