"""list_exam_bank — overview of exam_bank collections and papers (not KB)."""

from __future__ import annotations

import json

from langchain.tools import tool


@tool("list_exam_bank", parse_docstring=True)
def list_exam_bank_tool(paper_limit: int = 20) -> str:
    """List exam-bank collections and ingested papers. Use when the user asks what is in 题库.

    Do NOT use list_kb_sources for 题库 questions — knowledge base and exam bank are separate.

    Args:
        paper_limit: Max recent source papers to include (1-50).
    """
    from exam_bank.chat_exam_gate import build_exam_bank_overview

    lim = max(1, min(50, int(paper_limit or 20)))
    overview = build_exam_bank_overview(paper_limit=lim)
    guidance = (
        "这是试卷题库数据，不是向量知识库。请用表格展示题库与试卷；"
        "禁止把知识库 PDF/TXT 当作题库内容。若用户要做题，再调 search_exam_papers / present_exam_paper。"
    )
    if overview["collection_count"] == 0 and overview["paper_count"] == 0:
        guidance = (
            "题库为空。引导用户到 Admin「数据入库 → 试卷题库」入库；"
            "不要改用 list_kb_sources 或编造试卷。"
        )
    return json.dumps(
        {
            "ok": True,
            "system": "exam_bank",
            "not": "knowledge_base",
            **overview,
            "guidance": guidance,
        },
        ensure_ascii=False,
        indent=2,
    )
