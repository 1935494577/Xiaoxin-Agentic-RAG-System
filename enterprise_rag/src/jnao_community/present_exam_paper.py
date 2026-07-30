"""present_exam_paper — return chat paper JSON / fence hint for Chat UI."""

from __future__ import annotations

import json

from langchain.tools import tool


@tool("present_exam_paper", parse_docstring=True)
def present_exam_paper_tool(source_paper_id: str) -> str:
    """Load a structured exam paper for the chat ExamPaperCard (no answers).

    Args:
        source_paper_id: UUID of an ingested source paper in the exam bank.
    """
    from exam_bank.chat_paper import build_chat_paper

    sid = (source_paper_id or "").strip()
    if not sid:
        return json.dumps(
            {"ok": False, "error": "missing_source_paper_id", "message": "请提供 source_paper_id"},
            ensure_ascii=False,
        )
    paper = build_chat_paper(sid, include_answers=False)
    if not paper.get("ok"):
        return json.dumps(paper, ensure_ascii=False)
    # Fence for Chat MessageBubble + structured payload for tool_trace parsers
    fence = (
        "```exam_paper\n"
        + json.dumps(
            {
                "type": "exam_paper",
                "source_paper_id": paper["source_paper_id"],
                "paper_id": paper.get("paper_id"),
                "title": paper.get("title"),
            },
            ensure_ascii=False,
        )
        + "\n```"
    )
    return json.dumps(
        {
            "ok": True,
            "ui_block": {
                "type": "exam_paper",
                "source_paper_id": paper["source_paper_id"],
                "paper_id": paper.get("paper_id"),
                "title": paper.get("title"),
            },
            "paper": paper,
            "assistant_hint": (
                f"已为你准备标准卷面《{paper.get('title') or '试卷'}》。"
                f"请在回复中原样附上以下代码块，并提示用户点击「开始答题」：\n{fence}"
            ),
        },
        ensure_ascii=False,
        indent=2,
    )
