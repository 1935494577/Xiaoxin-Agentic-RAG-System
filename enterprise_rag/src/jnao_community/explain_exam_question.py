"""explain_exam_question — LLM step-by-step explanation for one bank question."""

from __future__ import annotations

import json

from langchain.tools import tool


@tool("explain_exam_question", parse_docstring=True)
def explain_exam_question_tool(
    question_id: str,
    user_answer: str = "",
) -> str:
    """Explain one exam-bank question with LLM (step-by-step solution).

    Use after the user submits a paper or asks to explain a specific item
    (e.g. 讲解第3题、为什么选A、主观题怎么写).

    Args:
        question_id: UUID of the question in exam_bank.
        user_answer: Optional user answer for personalized feedback.
    """
    from exam_bank.exam_tutor import explain_question_by_id

    qid = (question_id or "").strip()
    if not qid:
        return json.dumps(
            {"ok": False, "error": "missing_question_id", "message": "请提供 question_id"},
            ensure_ascii=False,
        )
    result = explain_question_by_id(qid, user_answer=(user_answer or "").strip())
    if not result.get("ok"):
        return json.dumps(result, ensure_ascii=False, indent=2)
    hint = (
        f"已生成第 {result.get('question_id', qid)} 题的讲解。"
        "请用 Markdown 向用户呈现 explanation 字段；"
        "若 is_correct 为 false，指出错因；主观题可结合 score_hint 与 key_points。"
        "公式使用 $...$ 定界符。"
    )
    return json.dumps({**result, "assistant_hint": hint}, ensure_ascii=False, indent=2)
