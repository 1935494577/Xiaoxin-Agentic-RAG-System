"""Split exam paper text into per-question draft items (rules-first)."""

from __future__ import annotations

import re
from typing import Any

from exam_bank.section_detect import detect_sections_rules
from exam_bank.subject_catalog import qtype_label

# Top-level question numbers only: 1. / 1、 / 1．  (NOT (1) sub-questions)
_ITEM_START_RE = re.compile(r"^\s*(?P<n1>\d+)\s*[.、．]\s*")

_OPTION_RE = re.compile(r"^[A-Da-d][.、．)\s]")

_ANSWER_MARK_RE = re.compile(r"^【\s*答案\s*】\s*(.*)$")
_ANALYSIS_MARK_RE = re.compile(r"^【\s*(?:解析|详解|分析)\s*】\s*(.*)$")

_JUNK_STEM_RE = re.compile(
    r"^(?:"
    r"注意事项|答题前|答卷前|考生须知|考生务必|装订线|密[封閉]线|准考证|姓名|考号|"
    r"用\s*2?\s*B\s*铅笔|用黑色|请将答案|本试卷|共\s*\d+\s*页|"
    r"第[一二三四五六七八九十]+部分|一、选择题.*本大题|"
    r"满分|考试时间|考试结束后|将本试卷|"
    r"写作词数|写[作文]词数|词数应[为在]|短文词数|"
    r"注意\s*[:：]|回答选择题时|选出每小题答案后|"
    r"请按如下格式|你的观点|你的设想|"
    r"答题时[，,].*答题纸|在本试题卷上的作答一律无效"
    r")"
)


def _looks_like_junk_stem(stem: str) -> bool:
    s = (stem or "").strip()
    if not s:
        return True
    if len(s) < 8 and re.match(r"^[\d一二三四五六七八九十]+[、.．]", s):
        return True
    if _JUNK_STEM_RE.search(s):
        return True
    if "选择题" in s and "本大题" in s and "（" in s and "）" in s and "下列" not in s:
        if not re.search(r"[（(]\s*[）)]|_{2,}|【答案】", s):
            if s.count("。") >= 2 and "已知" not in s and "设" not in s:
                return True
    return False


def _cn_section_qtype_map(text: str) -> list[tuple[int, str]]:
    """Map 1-based start_line -> qtype from section headings (一、 / 第X部分)."""
    sections = detect_sections_rules(text)
    out: list[tuple[int, str]] = []
    for s in sections:
        start = int(s.get("start_line") or 1)
        qt = str(s.get("qtype") or "other")
        # Skip noisy custom headings from English numbered stems mistaken as sections
        if qt.startswith("custom:"):
            continue
        out.append((start, qt))
    out.sort(key=lambda x: x[0])
    return out


def _qtype_at_line(line_no: int, section_starts: list[tuple[int, str]]) -> str:
    current = "other"
    for start, qt in section_starts:
        if line_no >= start:
            current = qt
        else:
            break
    return current


def parse_embedded_answer_blocks(block_lines: list[str]) -> tuple[list[str], str, str]:
    """
    Split question body lines from trailing 【答案】/【解析】 blocks.
    Returns (body_lines, answer, analysis).
    """
    body: list[str] = []
    answer = ""
    analysis_parts: list[str] = []
    mode: str | None = None  # None | answer | analysis
    for line in block_lines:
        s = line.strip()
        am = _ANSWER_MARK_RE.match(s)
        if am:
            mode = "answer"
            if am.group(1).strip():
                answer = am.group(1).strip()
            continue
        pm = _ANALYSIS_MARK_RE.match(s)
        if pm:
            mode = "analysis"
            if pm.group(1).strip():
                analysis_parts.append(pm.group(1).strip())
            continue
        if mode == "answer":
            # stop answer on 故选 / next structural mark already handled
            if s.startswith("【"):
                # another mark
                pm2 = _ANALYSIS_MARK_RE.match(s)
                if pm2:
                    mode = "analysis"
                    if pm2.group(1).strip():
                        analysis_parts.append(pm2.group(1).strip())
                continue
            if not answer:
                answer = s
            else:
                # multi-line answer rare — append
                answer = f"{answer} {s}".strip()
            continue
        if mode == "analysis":
            analysis_parts.append(line)
            continue
        body.append(line)
    analysis = "\n".join(analysis_parts).strip()
    # normalize 故选：X into answer if answer empty
    if not answer:
        for ln in analysis_parts:
            m = re.search(r"故选\s*[:：]?\s*([A-Da-d]+)", ln)
            if m:
                answer = m.group(1).upper()
                break
    return body, answer, analysis


def _extract_options(block_lines: list[str]) -> tuple[str, list[str]]:
    stem_lines: list[str] = []
    options: list[str] = []
    for line in block_lines:
        s = line.strip()
        if s.startswith("【"):
            # should already be stripped by parse_embedded; keep out of options
            if options:
                break
            stem_lines.append(line)
            continue
        if _OPTION_RE.match(s):
            options.append(s)
        else:
            if options:
                # trailing after options (e.g. 点睛) — ignore for stem
                continue
            stem_lines.append(line)
    if options:
        stem_only: list[str] = []
        for line in block_lines:
            s = line.strip()
            if _OPTION_RE.match(s) or s.startswith("【"):
                break
            stem_only.append(line)
        return "\n".join(stem_only).strip(), options
    return "\n".join(stem_lines).strip(), options


def split_items_rules(text: str, *, subject: str = "") -> list[dict[str, Any]]:
    """Split paper text into draft question items by numbered stems."""
    del subject
    raw = text or ""
    lines = raw.splitlines()
    section_starts = _cn_section_qtype_map(raw)

    starts: list[tuple[int, str]] = []  # (line_idx0, question_no)
    for i, line in enumerate(lines):
        m = _ITEM_START_RE.match(line)
        if not m:
            continue
        no = m.group("n1") or ""
        starts.append((i, str(no)))

    items: list[dict[str, Any]] = []
    for idx, (start_i, qno) in enumerate(starts):
        end_i = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        block = lines[start_i:end_i]
        first = block[0] if block else ""
        m = _ITEM_START_RE.match(first)
        rest_first = first[m.end() :] if m else first
        body_lines = [rest_first] + list(block[1:])
        body_lines, answer, analysis = parse_embedded_answer_blocks(body_lines)
        stem, options = _extract_options(body_lines)
        if not stem and not options:
            continue
        # 空题干但有选项（完形选项行）保留；说明性中文题干丢弃
        if stem and _looks_like_junk_stem(stem) and not options:
            continue
        if (
            stem
            and _looks_like_junk_stem(stem)
            and options
            and not re.search(r"[A-Za-z]{3,}", stem)
        ):
            continue
        qt = _qtype_at_line(start_i + 1, section_starts)
        if options and (qt == "other" or str(qt).startswith("custom:")):
            qt = "choice"
        items.append(
            {
                "question_no": qno,
                "qtype": qt,
                "label": qtype_label(qt),
                "stem": stem,
                "options": options,
                "answer": answer,
                "analysis": analysis,
                "selected": True,
            }
        )
    return items


def parse_answer_key(answer_text: str) -> dict[str, str]:
    """Parse answer sheet lines into question_no -> answer text."""
    out: dict[str, str] = {}
    for line in (answer_text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(
            r"^(?:第?\s*)?(\d+)\s*[.、．:：)）\s]\s*(.+)$",
            s,
        )
        if not m:
            m = re.match(r"^[(（]\s*(\d+)\s*[)）]\s*(.+)$", s)
        if not m:
            continue
        no, ans = m.group(1), m.group(2).strip()
        if no and ans:
            out[no] = ans
    return out


def parse_paper_items(
    text: str,
    *,
    subject: str = "",
    grade: str = "",
    region: str = "",
    stage: str = "",
    use_llm: bool = True,
    clean: bool = True,
) -> dict[str, Any]:
    """LLM-first item extract; rules when use_llm=False. Default cleans paper first."""
    from exam_bank.paper_router import analyze_paper

    raw = text or ""
    clean_meta: dict[str, Any] = {}
    working = raw
    if clean:
        from exam_bank.paper_clean import clean_exam_paper

        clean_meta = clean_exam_paper(raw)
        working = str(clean_meta.get("cleaned") or raw)

    if use_llm:
        from exam_bank.llm_ingest import extract_items_with_llm

        llm_items = extract_items_with_llm(
            working,
            subject=subject,
            grade=grade,
            region=region,
            stage=stage,
        )
        if llm_items and llm_items.get("items"):
            analysis = analyze_paper(
                working, subject=subject, grade=grade, use_llm=False
            )
            items = list(llm_items["items"])
            return {
                **analysis,
                **llm_items,
                "items": items,
                "item_count": int(llm_items.get("item_count") or len(items)),
                "subject": subject or analysis.get("subject") or "",
                "grade": grade or analysis.get("grade") or "",
                "region": region or "",
                "clean_applied": bool(clean),
                "cleaned_text": working if clean else "",
                "clean_warnings": list(clean_meta.get("warnings") or []),
                "clean_stats": dict(clean_meta.get("stats") or {}),
            }
        analysis = analyze_paper(working, subject=subject, grade=grade, use_llm=False)
        detail = {}
        if isinstance(llm_items, dict):
            detail = llm_items
        return {
            **analysis,
            "items": [],
            "item_count": 0,
            "answers_embedded": False,
            "skipped_non_questions": 0,
            "region": region or "",
            "router": str(detail.get("router") or "llm_failed"),
            "note": "llm_items_unavailable",
            "error": str(detail.get("error") or "llm_extract_failed"),
            "message": str(
                detail.get("message")
                or "大模型拆题未成功（请检查 API Key / 模型配置，或稍后重试）。未使用规则拆题，以免把注意事项当题目。"
            ),
            "model": detail.get("model") or "",
            "api_base": detail.get("api_base") or "",
            "raw_preview": detail.get("raw_preview") or "",
            "clean_applied": bool(clean),
            "cleaned_text": working if clean else "",
            "clean_warnings": list(clean_meta.get("warnings") or []),
        }

    analysis = analyze_paper(working, subject=subject, grade=grade, use_llm=False)
    items = split_items_rules(working, subject=subject or analysis.get("subject") or "")
    with_ans = sum(1 for it in items if (it.get("answer") or "").strip())
    answers_embedded = bool(items) and (with_ans / max(len(items), 1) >= 0.5)
    return {
        **analysis,
        "items": items,
        "item_count": len(items),
        "answers_embedded": answers_embedded,
        "skipped_non_questions": 0,
        "region": region or "",
        "note": analysis.get("note") or "",
        "router": "rules",
        "clean_applied": bool(clean),
        "cleaned_text": working if clean else "",
        "clean_warnings": list(clean_meta.get("warnings") or []),
        "clean_stats": dict(clean_meta.get("stats") or {}),
        "removed_sections": list(clean_meta.get("removed_sections") or []),
    }
