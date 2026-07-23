"""Detect exam section headings like 「一、选择题」 (rules)."""

from __future__ import annotations

import re
from typing import Any

from exam_bank.subject_catalog import normalize_qtype, qtype_label

_HEADING_RE = re.compile(
    r"^\s*([一二三四五六七八九十百零0-9]+)[、.．\.]\s*(.+?)\s*$",
)


def detect_sections_rules(text: str, *, subject: str = "") -> list[dict[str, Any]]:
    del subject  # subject reserved for future weighted aliases
    lines = (text or "").splitlines()
    sections: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line.strip())
        if not m:
            continue
        heading_raw = m.group(2).strip()
        heading = re.split(r"[（(【\s]", heading_raw, maxsplit=1)[0].strip()
        qt = normalize_qtype(heading)
        sections.append(
            {
                "heading": heading_raw,
                "qtype": qt,
                "label": qtype_label(qt),
                "approx_count": 0,
                "start_line": i + 1,
            }
        )
    return sections


def detect_sections(
    text: str,
    *,
    subject: str = "",
    use_llm: bool = False,
) -> list[dict[str, Any]]:
    """Compat: rules-only list. Prefer ``paper_router.analyze_paper`` for LLM."""
    del use_llm
    return detect_sections_rules(text, subject=subject)


def detect_sections_with_optional_llm(
    text: str,
    *,
    subject: str = "",
    grade: str = "",
    use_llm: bool = True,
) -> dict[str, Any]:
    """Default LLM-first via paper_router; rules fallback."""
    from exam_bank.paper_router import analyze_paper

    return analyze_paper(text, subject=subject, grade=grade, use_llm=use_llm)
