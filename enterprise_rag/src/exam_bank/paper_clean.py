"""Clean exam paper text before split — strip notices, normalize inline options."""

from __future__ import annotations

import re
from typing import Any

_HEADER_NOISE_RE = re.compile(
    r"^(?:绝密|启用前|机密|内部资料|\*{1,3}\s*绝密).*$",
    re.M,
)

_SECTION_START_RE = re.compile(
    r"^[一二三四五六七八九十百零]+[、.．]\s*(?:选择题|填空题|解答题|计算题|实验题|材料题|简答题|作文|阅读)",
)

_NOTICE_START_RE = re.compile(r"^注意事项\s*[:：]?")

# A. xxxB. yyy or A．xB．y — split glued options on one line
_INLINE_OPT_SPLIT_RE = re.compile(
    r"(?<![\[])(?P<head>[A-Da-d])\s*[.、．)]\s*"
)


def split_inline_options_line(line: str) -> list[str]:
    """If a line has multiple A/B/C/D markers, split into separate option lines."""
    s = (line or "").strip()
    if not s:
        return []
    # Use . ． ) only — Chinese顿号 A、B、C in stems must not split
    markers = list(re.finditer(r"[A-Da-d]\s*[.．)]", s))
    if len(markers) < 2:
        return [s]
    first = markers[0].group()[0].upper()
    if first not in {"A", "B", "C", "D"}:
        return [s]
    parts = re.split(r"(?=[A-Da-d]\s*[.．)])", s)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        p = re.sub(r"^([A-Da-d])\s*[.、．)]\s*", r"\1. ", p, count=1)
        out.append(p.strip())
    return out if len(out) >= 2 else [s]


def clean_exam_paper(text: str) -> dict[str, Any]:
    """
    Normalize exam paper text for splitting.

    - Drop header noise (绝密/启用前)
    - Drop 注意事项 block until first 一、选择题… section
    - Split glued inline options
    - Preserve [[EQ:n]] placeholders
    """
    raw = text or ""
    removed: list[str] = []
    warnings: list[str] = []

    lines = [ln.rstrip() for ln in raw.splitlines()]
    # strip pure header noise lines at top
    while lines and (
        not lines[0].strip()
        or _HEADER_NOISE_RE.match(lines[0].strip())
        or lines[0].strip() in {"★", "★ 启用前", "绝密 ★ 启用前"}
    ):
        if lines[0].strip():
            removed.append(lines[0].strip())
        lines.pop(0)

    # find 注意事项 and cut until section heading
    notice_idx = None
    section_idx = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if notice_idx is None and _NOTICE_START_RE.match(s):
            notice_idx = i
        if _SECTION_START_RE.match(s):
            section_idx = i
            break

    if notice_idx is not None and section_idx is not None and section_idx > notice_idx:
        chunk = lines[notice_idx:section_idx]
        removed.append("注意事项")
        # also drop numbered notice items only in that range — whole block
        lines = lines[:notice_idx] + lines[section_idx:]
        warnings.append(f"stripped_notice_lines:{len(chunk)}")
    elif notice_idx is not None and section_idx is None:
        warnings.append("notice_without_section")

    # drop empty leading meta lines that are only "本试卷共…满分" before first section
    # keep title lines (年…考试 / 数学) — useful metadata in stem source paper

    out_lines: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        # expand inline options
        parts = split_inline_options_line(s)
        out_lines.extend(parts)

    cleaned = "\n".join(out_lines)
    # collapse excessive blank (already stripped)
    stats = {
        "line_count": len(out_lines),
        "eq_placeholders": len(re.findall(r"\[\[EQ:\d+\]\]", cleaned)),
        "removed_count": len(removed),
    }
    return {
        "cleaned": cleaned,
        "removed_sections": removed,
        "warnings": warnings,
        "stats": stats,
    }
