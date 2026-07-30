"""Detect exam section headings like 「一、选择题」 / 「第一部分 听力」 (rules)."""

from __future__ import annotations

import re
from typing import Any

from exam_bank.subject_catalog import normalize_qtype, qtype_label

_HEADING_RE = re.compile(
    r"^\s*([一二三四五六七八九十百零0-9]+)[、.．\.]\s*(.+?)\s*$",
)

# 高考英语等：第一部分 听力 / 第三部分 语言运用（可出现在双栏 PDF 行中部）
_PART_ANYWHERE_RE = re.compile(
    r"第\s*([一二三四五六七八九十百零0-9]+)\s*部分\s*[:：\s]*"
    r"(听力|阅读理解|阅读|完形填空|完型填空|完形|完型|写作|书面表达|"
    r"语言运用|英语知识运用|知识运用)"
)

_JIE_ANYWHERE_RE = re.compile(
    r"第\s*([一二三四五六七八九十百零0-9]+)\s*节\s*"
    r"(?:[（(][^）)]*[）)])?\s*[:：\s]*"
    r"(听力|阅读理解|阅读|完形填空|完型填空|完形|完型|语法填空|写作|书面表达)?"
)

_PART_TITLE_TO_QTYPE: dict[str, str] = {
    "听力": "listening",
    "阅读": "reading",
    "阅读理解": "reading",
    "完形填空": "cloze",
    "完型填空": "cloze",
    "完形": "cloze",
    "完型": "cloze",
    "写作": "writing",
    "书面表达": "writing",
    # 语言运用：默认完形；第二节语法填空由 _jie 上下文纠正为 fill
    "语言运用": "cloze",
    "英语知识运用": "cloze",
    "知识运用": "cloze",
    "语法填空": "fill",
}

_FILL_HINT_RE = re.compile(r"语法填空|在空白处填|填入\s*\d+\s*个适当")
_CLOZE_HINT_RE = re.compile(r"完形|完型")
_READING_HINT_RE = re.compile(r"阅读下列短文|七选五|阅读下面短文[^，]{0,8}从每题")
_WRITING_HINT_RE = re.compile(r"书面表达|写作词数|短文改错")
_LISTENING_HINT_RE = re.compile(r"听下面|听第\s*\d+\s*段|每段对话")


def _qtype_from_part_title(title: str) -> str:
    t = (title or "").strip()
    if t in _PART_TITLE_TO_QTYPE:
        return _PART_TITLE_TO_QTYPE[t]
    return normalize_qtype(t)


def _hint_qtype_in_window(lines: list[str], start_i: int, window: int = 4) -> str | None:
    """Infer qtype from lines belonging to this 节 only (stop at next 部分/节)."""
    end = min(len(lines), start_i + max(1, window))
    for j in range(start_i + 1, min(len(lines), start_i + 12)):
        if _PART_ANYWHERE_RE.search(lines[j]) or _JIE_ANYWHERE_RE.search(lines[j]):
            end = j
            break
        end = j + 1
    chunk = "\n".join(lines[start_i:end])
    if _FILL_HINT_RE.search(chunk):
        return "fill"
    if _CLOZE_HINT_RE.search(chunk):
        return "cloze"
    if _READING_HINT_RE.search(chunk):
        return "reading"
    if _WRITING_HINT_RE.search(chunk):
        return "writing"
    if _LISTENING_HINT_RE.search(chunk):
        return "listening"
    return None


def detect_sections_rules(text: str, *, subject: str = "") -> list[dict[str, Any]]:
    del subject  # subject reserved for future weighted aliases
    lines = (text or "").splitlines()
    sections: list[dict[str, Any]] = []
    seen_starts: set[int] = set()

    def _add(start_line: int, heading: str, qt: str) -> None:
        if start_line in seen_starts:
            return
        seen_starts.add(start_line)
        sections.append(
            {
                "heading": heading,
                "qtype": qt,
                "label": qtype_label(qt),
                "approx_count": 0,
                "start_line": start_line,
            }
        )

    for i, line in enumerate(lines):
        raw = line.strip()
        if not raw:
            continue

        # 1) Classic 「一、选择题」
        m = _HEADING_RE.match(raw)
        if m:
            heading_raw = m.group(2).strip()
            heading = re.split(r"[（(【\s:：]", heading_raw, maxsplit=1)[0].strip()
            if not heading:
                # e.g. 「19.（1）设函数」→ heading empty → must not reset section to other
                pass
            elif "多项" in heading_raw or "多选" in heading_raw:
                _add(i + 1, heading_raw, "multi")
            else:
                qt = normalize_qtype(heading)
                # Skip English/math numbered stems mistaken as sections
                if m.group(1).isdigit() and (
                    qt == "other" or str(qt).startswith("custom:")
                ):
                    pass
                else:
                    _add(i + 1, heading_raw, qt)

        # 2) 「第X部分 听力/阅读/…」 anywhere on the line (PDF dual-column)
        for pm in _PART_ANYWHERE_RE.finditer(line):
            title = pm.group(2)
            qt = _qtype_from_part_title(title)
            _add(i + 1, pm.group(0).strip(), qt)

        # 3) 「第X节」+ optional title / following hints (语法填空等)
        for jm in _JIE_ANYWHERE_RE.finditer(line):
            titled = (jm.group(2) or "").strip()
            if titled:
                qt = _qtype_from_part_title(titled)
            else:
                hinted = _hint_qtype_in_window(lines, i, window=5)
                if not hinted:
                    continue
                qt = hinted
            _add(i + 1, jm.group(0).strip() or f"第{jm.group(1)}节", qt)

    sections.sort(key=lambda s: int(s.get("start_line") or 0))
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
