"""search_exam_papers — find ingested source papers for Chat exam flow."""

from __future__ import annotations

import json

from langchain.tools import tool


@tool("search_exam_papers", parse_docstring=True)
def search_exam_papers_tool(query: str, limit: int = 10) -> str:
    """Search the exam bank for ingested papers by title or filename.

    Args:
        query: Keywords such as year, subject, or paper title (e.g. 2024 gaokao).
        limit: Max results from 1 to 20.
    """
    from exam_bank import store

    q = (query or "").strip()
    if not q:
        return json.dumps(
            {
                "ok": False,
                "error": "missing_query",
                "message": "请提供检索关键词（年份/卷名等）",
                "hint": "若尚未入库，请到 Admin「数据入库 → 试卷题库」导入。",
            },
            ensure_ascii=False,
        )
    lim = max(1, min(20, int(limit or 10)))
    items = store.search_source_papers(q, limit=lim)
    slim = [
        {
            "id": it["id"],
            "title": it.get("title") or "",
            "source_filename": it.get("source_filename") or "",
            "collection_id": it.get("collection_id") or "",
            "question_count": len(it.get("question_ids") or []),
        }
        for it in items
    ]
    n = len(slim)
    guidance = ""
    if n == 0:
        guidance = (
            "未找到试卷。请引导用户到 Admin「数据入库 → 试卷题库」入库；"
            "不要用知识库长文冒充可答题卷。"
        )
    elif n == 1:
        guidance = (
            f"唯一命中，请立即调用 present_exam_paper(source_paper_id={slim[0]['id']!r})，"
            "并在回复中附上工具返回的 exam_paper 代码块。"
        )
    else:
        guidance = (
            "多条命中：列出标题与 id，请用户选择后再调用 present_exam_paper；禁止擅自挑选。"
            "也可在回复中附上 exam_candidates JSON 列表供前端点选。"
        )
    return json.dumps(
        {
            "ok": True,
            "q": q,
            "total": n,
            "items": slim,
            "ui_block": (
                {
                    "type": "exam_paper",
                    "source_paper_id": slim[0]["id"],
                    "paper_id": slim[0]["id"],
                    "title": slim[0]["title"],
                }
                if n == 1
                else {"type": "exam_candidates", "items": slim}
                if n > 1
                else None
            ),
            "guidance": guidance,
        },
        ensure_ascii=False,
        indent=2,
    )
