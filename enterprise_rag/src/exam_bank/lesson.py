"""P4: lesson plan outline from an assembled exam paper."""

from __future__ import annotations

from collections import Counter
from typing import Any

from exam_bank.subject_catalog import qtype_label


def render_lesson_outline(*, title: str, questions: list[dict[str, Any]]) -> str:
    """Rules-first lesson outline (stable without LLM)."""
    t = (title or "未命名试卷").strip()
    lines: list[str] = [
        f"教案大纲 — {t}",
        "",
        "## 一、教学目标",
        "- 掌握本卷涉及的核心知识点，能独立完成同难度练习。",
        "- 梳理易错点与解题步骤，形成可迁移的解题思路。",
        "",
        "## 二、知识点覆盖",
    ]
    tag_counts: Counter[str] = Counter()
    for q in questions:
        for tag in q.get("knowledge_tags") or []:
            s = str(tag).strip()
            if s:
                tag_counts[s] += 1
    if tag_counts:
        for tag, n in tag_counts.most_common(12):
            lines.append(f"- {tag}（{n} 题）")
    else:
        lines.append("- （本题库题目尚未标注知识点，可在入库时由模型自动打标）")

    lines.extend(["", "## 三、例题精讲（按题序）", ""])
    for i, q in enumerate(questions, start=1):
        qt = qtype_label(str(q.get("qtype") or "other"))
        diff = q.get("difficulty") or 3
        stem = (q.get("stem") or "").strip()
        preview = stem if len(stem) <= 80 else stem[:80] + "…"
        tags = "、".join(str(x) for x in (q.get("knowledge_tags") or [])[:5]) or "—"
        lines.append(f"### 例题 {i}（{qt} · 难度 {diff}）")
        lines.append(f"- 题干：{preview}")
        lines.append(f"- 知识点：{tags}")
        ans = (q.get("answer") or "").strip()
        if ans:
            lines.append(f"- 参考答案：{ans}")
        analysis = (q.get("analysis") or "").strip()
        if analysis:
            lines.append(f"- 讲解要点：{analysis}")
        else:
            lines.append("- 讲解要点：引导学生先审题 → 锁定知识点 → 规范书写步骤。")
        lines.append("")

    lines.extend(
        [
            "## 四、课堂活动建议",
            "1. 先练后讲：学生限时完成，教师巡视收集共性错误。",
            "2. 对照答案：小组互批，口述解题关键步骤。",
            "3. 变式巩固：针对高频错因布置 1～2 道同类题。",
            "",
            "## 五、课后作业",
            "- 错题订正并写清「错因 + 正确步骤」。",
            "- 从题库同知识点再抽 2 题巩固。",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def lesson_from_paper(paper_id: str) -> dict[str, Any]:
    from exam_bank import store
    from exam_bank.export_formats import _ordered_questions

    paper = store.get_paper(paper_id)
    if not paper:
        return {"ok": False, "error": "paper_not_found", "message": "试卷不存在"}
    questions = _ordered_questions(paper)
    if not questions:
        return {"ok": False, "error": "empty_paper", "message": "试卷没有题目"}
    md = render_lesson_outline(title=str(paper.get("title") or ""), questions=questions)
    return {
        "ok": True,
        "paper_id": paper_id,
        "title": paper.get("title") or "",
        "markdown": md,
        "question_count": len(questions),
    }
