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
    chapters_any: list[str] | None = None,
    regions_any: list[str] | None = None,
    years_any: list[str] | None = None,
) -> list[dict[str, Any]]:
    out = []
    tags_any = [t for t in (knowledge_tags_any or []) if t]
    chapters = [c for c in (chapters_any or []) if c]
    regions = [r for r in (regions_any or []) if r]
    years = [y for y in (years_any or []) if y]
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
        if chapters:
            if str(q.get("chapter") or "").strip() not in chapters:
                continue
        if regions:
            qreg = str(q.get("region") or "").strip()
            # 空地区视为继承题库地区，避免库内统计含题、组卷却被地区锁踢掉
            if qreg and qreg not in regions:
                continue
        if years:
            if str(q.get("year") or "").strip() not in years:
                continue
        out.append(q)
    return out


def render_markdown(
    *,
    title: str,
    ordered: list[dict[str, Any]],
    include_answers: bool,
) -> str:
    from exam_bank.paper_layout import render_formal_markdown

    return render_formal_markdown(
        title=title,
        questions=ordered,
        include_answers=include_answers,
    )


def _pick_for_qtype(
    group: list[dict[str, Any]],
    need_n: int,
    *,
    seed: int,
    qt: str,
    remaining_bands: dict[str, int] | None,
    allow_partial: bool = False,
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
    bands = dict(remaining_bands) if remaining_bands else None

    if bands:
        for band, want in list(bands.items()):
            if want <= 0 or len(picked) >= need_n:
                continue
            lo, hi = DIFFICULTY_BANDS[band]
            cand = [
                q
                for q in group
                if q["id"] not in used_ids and lo <= int(q.get("difficulty") or 0) <= hi
            ]
            take = min(want, need_n - len(picked), len(cand))
            if take < want and want > 0 and len(cand) < want:
                if allow_partial and cand:
                    take = min(want, need_n - len(picked), len(cand))
                else:
                    return {
                        "ok": False,
                        "error": "insufficient_difficulty",
                        "detail": {
                            "qtype": qt,
                            "label": qtype_label(qt),
                            "band": band,
                            "need": want,
                            "have": len(cand),
                            "message": (
                                f"题型「{qtype_label(qt)}」缺少"
                                f"「{DIFFICULTY_BAND_LABELS.get(band, band)}」难度："
                                f"需要 {want}，仅有 {len(cand)}"
                            ),
                        },
                    }
            for q in cand[:take]:
                picked.append(q)
                used_ids.add(q["id"])
                bands[band] = bands.get(band, 0) - 1

    for q in group:
        if len(picked) >= need_n:
            break
        if q["id"] in used_ids:
            continue
        picked.append(q)
        used_ids.add(q["id"])

    if len(picked) < need_n:
        if allow_partial and picked:
            return picked
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
    """Assemble with optional soft_fallback: progressively relax year/chapter/tag/band filters."""
    base = dict(spec or {})
    soft = bool(base.get("soft_fallback", False))
    notes: list[str] = []
    working = dict(base)

    relax_plan: list[tuple[str, Any, str] | None] = [
        None,
        ("years_any", [], "已放宽：取消优先年份限制"),
        ("chapters_any", [], "已放宽：取消章节限制"),
        ("knowledge_tags_any", [], "已放宽：按知识点精确匹配 → 不限标签"),
        ("by_difficulty_band", {}, "已放宽：取消整卷难度档约束"),
        ("by_qtype_band", {}, "已放宽：取消分题型难度档约束"),
        ("difficulty_min", None, "已放宽：取消难度下限"),
        ("difficulty_max", None, "已放宽：取消难度上限"),
        ("require_complete", False, "已放宽：允许选用待补全题目"),
        ("_allow_partial", True, "已按库内实际可用题量出卷"),
    ]

    last: dict[str, Any] = {"ok": False, "error": "assemble_failed"}
    for step in relax_plan:
        if step is not None:
            if not soft:
                break
            key, val, note = step
            # require_complete defaults True when absent — treat as "set" for relax
            cur = working.get(key)
            if key == "require_complete":
                if cur is False:
                    continue
                working[key] = val
                notes.append(note)
            elif key in ("difficulty_min", "difficulty_max"):
                if cur is None:
                    continue
                working[key] = val
                notes.append(note)
            elif key == "_allow_partial":
                if working.get("_allow_partial"):
                    continue
                working[key] = val
                notes.append(note)
            elif cur:
                working[key] = val
                notes.append(note)
            else:
                continue
        last = _assemble_paper_once(
            collection_id=collection_id,
            title=title,
            spec=working,
            include_answers=include_answers,
            tenant_id=tenant_id,
        )
        if last.get("ok"):
            last["fallback_applied"] = bool(notes)
            last["fallback_notes"] = list(notes)
            return last
        if not soft:
            last["fallback_applied"] = False
            last["fallback_notes"] = []
            return last
    last["fallback_applied"] = bool(notes)
    last["fallback_notes"] = list(notes)
    return last


def _assemble_paper_once(
    *,
    collection_id: str,
    title: str,
    spec: dict[str, Any] | None = None,
    include_answers: bool = True,
    tenant_id: str = DEFAULT_TENANT,
) -> dict[str, Any]:
    spec = dict(spec or {})
    allow_partial = bool(spec.get("_allow_partial") or spec.get("allow_partial"))
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
    regions_any = spec.get("regions_any")
    if regions_any is not None and not isinstance(regions_any, list):
        regions_any = []
    years_any = spec.get("years_any")
    if years_any is not None and not isinstance(years_any, list):
        years_any = []
    chapters_any = spec.get("chapters_any")
    if chapters_any is not None and not isinstance(chapters_any, list):
        chapters_any = []
    seed = int(spec.get("seed") if spec.get("seed") is not None else 0)

    def _pool_kwargs() -> dict[str, Any]:
        return {
            "difficulty_min": int(dmin) if dmin is not None else None,
            "difficulty_max": int(dmax) if dmax is not None else None,
            "knowledge_tags_any": [str(x) for x in (tags_any or [])],
            "chapters_any": [str(x) for x in (chapters_any or [])],
            "regions_any": [str(x) for x in (regions_any or [])],
            "years_any": [str(x) for x in (years_any or [])],
        }

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
                **_pool_kwargs(),
            )
            require_complete = spec.get("require_complete")
            if require_complete is None:
                require_complete = True
            if require_complete:
                from exam_bank.question_quality import is_question_incomplete

                pool_all = [q for q in pool_all if not is_question_incomplete(q)]
            # Restrict to requested qtypes
            wanted = set(by_qtype)
            pool_all = [q for q in pool_all if normalize_qtype(str(q.get("qtype"))) in wanted]
            for band, need in remaining_bands.items():
                lo, hi = DIFFICULTY_BANDS[band]
                have = sum(1 for q in pool_all if lo <= int(q.get("difficulty") or 0) <= hi)
                if have < need and not allow_partial:
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

    # Per-qtype difficulty bands: { "choice": { "easy": 2, "mid": 1, "hard": 1 }, ... }
    raw_qtype_bands = spec.get("by_qtype_band") or {}
    qtype_bands: dict[str, dict[str, int]] = {}
    if isinstance(raw_qtype_bands, dict) and raw_qtype_bands:
        for k, v in raw_qtype_bands.items():
            qt = normalize_qtype(str(k))
            if not isinstance(v, dict):
                continue
            parsed = {
                str(bk): int(bv)
                for bk, bv in v.items()
                if str(bk) in DIFFICULTY_BANDS and int(bv) > 0
            }
            if parsed:
                qtype_bands[qt] = parsed
                band_sum = sum(parsed.values())
                if qt in by_qtype and by_qtype[qt] != band_sum:
                    return {
                        "ok": False,
                        "error": "invalid_spec",
                        "detail": {
                            "qtype": qt,
                            "message": (
                                f"题型「{qtype_label(qt)}」难度合计 {band_sum} "
                                f"与需要道数 {by_qtype[qt]} 不一致"
                            ),
                        },
                    }
                if qt not in by_qtype:
                    by_qtype[qt] = band_sum

    pool, _ = store.list_questions(
        collection_id=collection_id,
        status="published",
        limit=500,
        offset=0,
    )
    pool = _filter_pool(
        pool,
        **_pool_kwargs(),
    )
    # Closed loop: default exclude incomplete (empty options/answer)
    require_complete = spec.get("require_complete")
    if require_complete is None:
        require_complete = True
    if require_complete:
        from exam_bank.question_quality import is_question_incomplete

        pool = [q for q in pool if not is_question_incomplete(q)]

    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    # Global bands are shared across qtypes (legacy); per-qtype bands take precedence
    shared_bands = dict(remaining_bands) if remaining_bands and not qtype_bands else None
    for qt, need_n in by_qtype.items():
        if need_n <= 0:
            continue
        group = [q for q in pool if normalize_qtype(str(q.get("qtype"))) == qt]
        bands_for_qt = qtype_bands.get(qt)
        if bands_for_qt is not None:
            pick_bands = dict(bands_for_qt)
        else:
            pick_bands = shared_bands
        result = _pick_for_qtype(
            group,
            need_n,
            seed=seed,
            qt=qt,
            remaining_bands=pick_bands,
            allow_partial=allow_partial,
        )
        if isinstance(result, dict) and result.get("ok") is False:
            return result
        assert isinstance(result, list)
        selected.extend(result)
        counts[qt] = len(result)
        # Consume from shared global bands when used
        if shared_bands is not None and bands_for_qt is None:
            for q in result:
                b = _band_of(int(q.get("difficulty") or 3))
                if b in shared_bands:
                    shared_bands[b] = shared_bands.get(b, 0) - 1

    if not selected:
        return {
            "ok": False,
            "error": "insufficient_questions",
            "detail": {"message": "筛选后没有可用题目"},
        }

    from exam_bank.question_quality import normalize_question_display

    selected = [normalize_question_display(q) for q in selected]
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
        "questions": selected,
        "counts": counts,
        "markdown": md,
    }
