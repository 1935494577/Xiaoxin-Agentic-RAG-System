"""Formal Chinese exam paper layout helpers (卷面还原)."""

from __future__ import annotations

from typing import Any

from exam_bank.subject_catalog import qtype_label

_CN_ORDINALS = "一二三四五六七八九十"


def cn_section_index(i: int) -> str:
    """0-based index → 一/二/…/十/十一…"""
    n = i + 1
    if 1 <= n <= 10:
        return _CN_ORDINALS[n - 1]
    if n < 20:
        return "十" + (_CN_ORDINALS[n - 11] if n > 10 else "")
    return str(n)


def group_questions_by_qtype(
    questions: list[dict[str, Any]],
) -> tuple[list[str], dict[str, list[dict[str, Any]]]]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for q in questions:
        qt = str(q.get("qtype") or "other")
        if qt not in by_type:
            order.append(qt)
            by_type[qt] = []
        by_type[qt].append(q)
    return order, by_type


def section_heading(section_i: int, qtype: str, count: int) -> str:
    label = qtype_label(qtype)
    # 正式卷常见：「一、选择题（本大题共 n 小题）」
    return f"{cn_section_index(section_i)}、{label}（本大题共 {count} 小题）"


def render_formal_markdown(
    *,
    title: str,
    questions: list[dict[str, Any]],
    include_answers: bool,
    subtitle: str = "",
) -> str:
    """Render paper body in formal exam style (not blog markdown)."""
    lines: list[str] = []
    t = (title or "未命名试卷").strip()
    lines.append(t)
    lines.append("")
    if subtitle.strip():
        lines.append(subtitle.strip())
        lines.append("")
    lines.append("姓名__________  班级__________  考号__________")
    lines.append("")

    order, by_type = group_questions_by_qtype(questions)
    n = 1
    for si, qt in enumerate(order):
        group = by_type.get(qt) or []
        if not group:
            continue
        lines.append(section_heading(si, qt, len(group)))
        lines.append("")
        for q in group:
            stem = (q.get("stem") or "").strip()
            lines.append(f"{n}. {stem}")
            opts = [str(o).strip() for o in (q.get("options") or []) if str(o).strip()]
            if opts:
                # 正式卷选项独立成行，全角缩进与纸质卷一致
                for o in opts:
                    lines.append(f"　　{o}")
            lines.append("")
            n += 1

    if include_answers:
        lines.append("—" * 16)
        lines.append("参考答案与解析（考生勿看）")
        lines.append("")
        n = 1
        for q in questions:
            lines.append(f"{n}. 【答案】{q.get('answer') or '（略）'}")
            analysis = (q.get("analysis") or "").strip()
            if analysis:
                lines.append(f"　　【解析】{analysis}")
            lines.append("")
            n += 1

    return "\n".join(lines).rstrip() + "\n"
