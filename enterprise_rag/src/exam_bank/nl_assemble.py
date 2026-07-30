"""Parse natural-language assemble requests into assemble specs (P1)."""

from __future__ import annotations

import re
from typing import Any

from exam_bank.subject_catalog import qtype_label

# 题型别名 → 标准 qtype
_QTYPE_ALIASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"选择|单选|多选"), "choice"),
    (re.compile(r"填空"), "fill"),
    (re.compile(r"计算"), "calc"),
    (re.compile(r"实验"), "experiment"),
    (re.compile(r"完形|完型"), "cloze"),
    (re.compile(r"阅读"), "reading"),
    (re.compile(r"写作|作文"), "writing"),
    (re.compile(r"听力"), "listening"),
    (re.compile(r"材料"), "material"),
    (re.compile(r"解答|大题|简答|证明|应用"), "short"),
]

_BAND_ALIASES = [
    (re.compile(r"简单|容易|基础"), "easy"),
    (re.compile(r"中等|中档|一般"), "mid"),
    (re.compile(r"困难|较难|很难|高难"), "hard"),
]

_GLOBAL_DIFF = [
    (re.compile(r"简单难度|偏易|基础卷"), "easy"),
    (re.compile(r"中等难度|中档难度|难度适中|中等"), "mid"),
    (re.compile(r"困难难度|偏难|高难度"), "hard"),
]


def _detect_qtype(chunk: str) -> str | None:
    for pat, qt in _QTYPE_ALIASES:
        if pat.search(chunk):
            return qt
    return None


def _extract_counts_in_parens(chunk: str) -> dict[str, int] | None:
    """Parse 简单2中等2困难1 inside a segment."""
    bands: dict[str, int] = {}
    for pat, band in _BAND_ALIASES:
        m = re.search(rf"(?:{pat.pattern})\s*[：:]?\s*(\d+)", chunk)
        if m and m.group(1):
            bands[band] = int(m.group(1))
    return bands or None


def _need_from_chunk(chunk: str) -> int | None:
    m = re.search(r"(\d+)\s*道?", chunk)
    if m:
        return int(m.group(1))
    return None


def parse_assemble_nl(text: str, *, default_title: str = "") -> dict[str, Any]:
    """
    Rules-first NL → assemble spec.

    Examples:
    - 高三数学浙江中等难度，选择 8 + 填空 4 + 解答 4
    - 选择题5道（简单2中等2困难1），填空题3道
    """
    raw = (text or "").strip()
    if not raw:
        return {"ok": False, "error": "nl_parse_empty", "message": "请输入组卷需求，例如：选择 8 + 填空 4，中等难度"}

    # Split into segments by common separators
    parts = re.split(r"[，,;；+\n]+|以及|和(?=\S*[选填解计])", raw)
    parts = [p.strip() for p in parts if p and p.strip()]

    by_qtype: dict[str, int] = {}
    by_qtype_band: dict[str, dict[str, int]] = {}

    for part in parts:
        qt = _detect_qtype(part)
        if not qt:
            continue
        bands = _extract_counts_in_parens(part)
        need = _need_from_chunk(part)
        if bands:
            band_sum = sum(bands.values())
            by_qtype[qt] = by_qtype.get(qt, 0) + band_sum
            merged = dict(by_qtype_band.get(qt) or {})
            for k, v in bands.items():
                merged[k] = merged.get(k, 0) + v
            by_qtype_band[qt] = merged
        elif need is not None and need > 0:
            by_qtype[qt] = by_qtype.get(qt, 0) + need

    if not by_qtype:
        return {
            "ok": False,
            "error": "nl_parse_empty",
            "message": "未能识别题型数量。示例：选择 8 + 填空 4 + 解答 4，中等难度",
        }

    # Global difficulty → fill bands if missing
    global_band: str | None = None
    for pat, band in _GLOBAL_DIFF:
        if pat.search(raw):
            global_band = band
            break

    if global_band:
        for qt, n in by_qtype.items():
            if qt not in by_qtype_band:
                by_qtype_band[qt] = {global_band: n}

    # Title hints
    title_bits: list[str] = []
    for label in ("高三", "高二", "高一", "初三", "初二", "初一", "数学", "语文", "英语", "物理", "化学", "浙江", "江苏", "北京", "上海"):
        if label in raw and label not in title_bits:
            title_bits.append(label)
    title = default_title.strip() or ("·".join(title_bits) + "组卷" if title_bits else "一句话组卷")

    summary = "、".join(f"{qtype_label(k)}{v}" for k, v in by_qtype.items())
    return {
        "ok": True,
        "title": title,
        "summary": summary,
        "spec": {
            "by_qtype": by_qtype,
            "by_qtype_band": by_qtype_band,
            "seed": abs(hash(raw)) % 10_000,
        },
        "message": f"将按「{summary}」组卷",
    }


def assemble_from_nl(
    *,
    collection_id: str,
    text: str,
    title: str = "",
    include_answers: bool = True,
    tenant_id: str = "internal",
    soft_fallback: bool = True,
) -> dict[str, Any]:
    from exam_bank import assemble

    parsed = parse_assemble_nl(text, default_title=title)
    if not parsed.get("ok"):
        return parsed
    spec = dict(parsed["spec"] or {})
    # Match auto-generate: default soft fallback so mid-band shortages still assemble
    if soft_fallback and "soft_fallback" not in spec:
        spec["soft_fallback"] = True
    result = assemble.assemble_paper(
        collection_id=collection_id,
        title=title.strip() or str(parsed.get("title") or "一句话组卷"),
        spec=spec,
        include_answers=include_answers,
        tenant_id=tenant_id,
    )
    if result.get("ok"):
        result["parsed_spec"] = parsed["spec"]
        result["nl_summary"] = parsed.get("summary") or ""
        notes = list(result.get("fallback_notes") or [])
        base_msg = str(parsed.get("message") or "")
        if notes:
            result["nl_message"] = f"{base_msg}（已智能放宽：{'；'.join(notes)}）"
        else:
            result["nl_message"] = base_msg
    return result
