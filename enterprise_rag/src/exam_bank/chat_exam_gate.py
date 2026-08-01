"""Deterministic exam-bank gate for Chat: sense papers then present UI blocks."""

from __future__ import annotations

import json
from typing import Any

from exam_bank import store
from exam_bank.exam_intent import (
    extract_exam_search_query,
    is_exam_inventory_intent,
    is_exam_take_intent,
)
from retrieval.retrieval_mode_router import resolve_exam_paper_hits
from exam_bank.subject_catalog import qtype_label


def _slim(it: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": it["id"],
        "title": it.get("title") or "",
        "source_filename": it.get("source_filename") or "",
        "collection_id": it.get("collection_id") or "",
        "question_count": len(it.get("question_ids") or []),
        "collection_name": it.get("collection_name") or "",
        "region": it.get("region") or "",
        "subject": it.get("subject") or "",
        "grade": it.get("grade") or "",
    }


def build_exam_bank_overview(
    *,
    paper_limit: int = 20,
    reader_user_id: str | None = None,
) -> dict[str, Any]:
    """Snapshot of exam_bank collections + recent source papers (not KB docs)."""
    cols = store.list_collections(reader_user_id=reader_user_id or None)
    collections_out: list[dict[str, Any]] = []
    total_questions = 0
    for c in cols:
        inv = store.collection_inventory(c["id"])
        qtotal = int(inv.get("total") or 0)
        total_questions += qtotal
        by_qt = inv.get("by_qtype") or {}
        qt_bits = [
            f"{qtype_label(k)} {v}"
            for k, v in sorted(by_qt.items(), key=lambda x: (-x[1], x[0]))
            if int(v) > 0
        ]
        collections_out.append(
            {
                "id": c["id"],
                "name": c.get("name") or "",
                "region": c.get("region") or "",
                "subject": c.get("subject") or "",
                "grade": c.get("grade") or "",
                "question_total": qtotal,
                "by_qtype_label": "、".join(qt_bits) if qt_bits else "暂无已发布题目",
            }
        )
    papers = [
        _slim(p)
        for p in store.list_recent_source_papers(
            limit=paper_limit,
            reader_user_id=reader_user_id,
        )
    ]
    return {
        "collection_count": len(collections_out),
        "question_total": total_questions,
        "paper_count": len(papers),
        "collections": collections_out,
        "papers": papers,
    }


def _inventory_gate(*, reader_user_id: str | None = None) -> dict[str, Any]:
    overview = build_exam_bank_overview(paper_limit=20, reader_user_id=reader_user_id)
    tool_trace = [
        {
            "tool": "list_exam_bank",
            "arguments": {},
            "output": json.dumps(
                {"ok": True, **{k: overview[k] for k in ("collection_count", "question_total", "paper_count")}},
                ensure_ascii=False,
            ),
            "ok": True,
        }
    ]
    cols = overview["collections"]
    papers = overview["papers"]

    if not cols and not papers:
        answer = (
            "当前**试卷题库为空**（这与向量**知识库**是两套系统）。\n\n"
            "请到 Admin **数据入库 → 试卷题库**（或题库矩阵「试卷入库」）导入整卷；\n"
            "知识文档通道只会进知识库，**不会**产生可作答的试卷。\n\n"
            "入库后可再说「题库里有什么」或「把某某卷拿出来做」。"
        )
        return {
            "ok": True,
            "handled": True,
            "mode": "inventory",
            "answer": answer,
            "ui_blocks": [],
            "tool_trace": tool_trace,
            "keywords": "",
            "hit_count": 0,
            "overview": overview,
        }

    lines: list[str] = [
        "以下是**试卷题库**（exam_bank）概况，**不是**向量知识库里的 PDF/TXT 文档。\n",
    ]
    if cols:
        lines.append("| 题库 | 地区/学科/年级 | 已发布题量 | 题型 |")
        lines.append("| --- | --- | ---: | --- |")
        for c in cols:
            meta = "/".join(
                x for x in [c.get("region") or "", c.get("subject") or "", c.get("grade") or ""] if x
            ) or "—"
            lines.append(
                f"| {c.get('name') or c['id']} | {meta} | {c.get('question_total', 0)} | "
                f"{c.get('by_qtype_label') or '—'} |"
            )
        lines.append("")
    if papers:
        lines.append("### 已入库试卷（可「拿出来做」）\n")
        lines.append("| 试卷 | 所属库 | 题量 |")
        lines.append("| --- | --- | ---: |")
        for p in papers:
            lines.append(
                f"| {p.get('title') or p['id']} | "
                f"{p.get('collection_name') or p.get('region') or '—'} | "
                f"{p.get('question_count', 0)} |"
            )
        lines.append("")
    else:
        lines.append(
            "尚无整卷入库记录；若题库里已有散题，可到 Admin 组卷，"
            "或通过「试卷入库」导入完整卷面后再做题。\n"
        )

    lines.append(
        f"合计：**{overview['collection_count']}** 个题库、"
        f"**{overview['question_total']}** 道已发布题、"
        f"**{overview['paper_count']}** 份入库试卷。\n\n"
        "若要作答，直接说「把某某卷拿出来做」。"
    )
    answer = "\n".join(lines)
    ui_blocks: list[dict[str, Any]] = []
    if len(papers) > 1:
        ui_blocks.append({"type": "exam_candidates", "items": papers})
    elif len(papers) == 1:
        one = papers[0]
        ui_blocks.append(
            {
                "type": "exam_paper",
                "source_paper_id": one["id"],
                "paper_id": one["id"],
                "title": one["title"],
            }
        )
    return {
        "ok": True,
        "handled": True,
        "mode": "inventory",
        "answer": answer,
        "ui_blocks": ui_blocks,
        "tool_trace": tool_trace,
        "keywords": "",
        "hit_count": len(papers) or len(cols),
        "overview": overview,
    }


def _take_empty_response(
    *,
    keywords: str,
    tool_trace: list[dict[str, Any]],
    message: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "handled": True,
        "mode": "take",
        "answer": message,
        "ui_blocks": [],
        "tool_trace": tool_trace,
        "keywords": keywords,
        "hit_count": 0,
    }


def resolve_exam_chat_gate(
    question: str,
    *,
    limit: int = 10,
    reader_user_id: str | None = None,
) -> dict[str, Any] | None:
    """
    If the user wants exam-bank content, search/list exam_bank and return a Chat gate payload.

    Returns None when intent does not match (caller continues normal RAG/Agent).
    """
    q_raw = (question or "").strip()
    if is_exam_inventory_intent(q_raw):
        return _inventory_gate(reader_user_id=reader_user_id)
    if not is_exam_take_intent(q_raw):
        return None

    keywords = extract_exam_search_query(q_raw)
    reader = reader_user_id
    hits: list[dict[str, Any]] = []
    exam_search_mode = "exact"
    if keywords:
        hits, exam_search_mode = resolve_exam_paper_hits(
            keywords,
            limit=limit,
            reader_user_id=reader,
        )

    tool_trace = [
        {
            "tool": "search_exam_papers",
            "arguments": {"query": keywords or q_raw, "search_mode": exam_search_mode},
            "output": json.dumps({"ok": True, "total": 0, "items": []}, ensure_ascii=False),
            "ok": True,
        }
    ]

    if not keywords:
        return _take_empty_response(
            keywords=keywords,
            tool_trace=tool_trace,
            message=(
                "请说明要做哪一份试卷（例如：2024 浙江高三数学卷），"
                "或先说「题库里有什么」查看已入库列表。\n\n"
                "我不会从知识库 PDF 里编造可答题卷。"
            ),
        )

    if not hits:
        return _take_empty_response(
            keywords=keywords,
            tool_trace=tool_trace,
            message=(
                f"题库中未找到匹配「{keywords}」的试卷（不是知识库）。\n\n"
                "请核对卷名/年份/地区，或到 Admin **数据入库 → 试卷题库** 入库后再试。"
            ),
        )

    slim = [_slim(h) for h in hits]
    tool_trace[0]["output"] = json.dumps(
        {"ok": True, "total": len(slim), "items": slim}, ensure_ascii=False
    )

    if len(slim) == 1:
        one = slim[0]
        fence = (
            "```exam_paper\n"
            + json.dumps(
                {
                    "type": "exam_paper",
                    "source_paper_id": one["id"],
                    "paper_id": one["id"],
                    "title": one["title"],
                },
                ensure_ascii=False,
            )
            + "\n```"
        )
        answer = (
            f"已从**题库**找到《{one['title'] or '试卷'}》。"
            f"请点击下方标准卷面的「开始答题」。\n\n{fence}"
        )
        tool_trace.append(
            {
                "tool": "present_exam_paper",
                "arguments": {"source_paper_id": one["id"]},
                "output": json.dumps(
                    {
                        "ok": True,
                        "ui_block": {
                            "type": "exam_paper",
                            "source_paper_id": one["id"],
                            "title": one["title"],
                        },
                    },
                    ensure_ascii=False,
                ),
                "ok": True,
            }
        )
        return {
            "ok": True,
            "handled": True,
            "mode": "take",
            "answer": answer,
            "ui_blocks": [
                {
                    "type": "exam_paper",
                    "source_paper_id": one["id"],
                    "paper_id": one["id"],
                    "title": one["title"],
                }
            ],
            "tool_trace": tool_trace,
            "keywords": keywords,
            "hit_count": 1,
        }

    cand_fence = (
        "```exam_candidates\n"
        + json.dumps({"items": slim}, ensure_ascii=False)
        + "\n```"
    )
    lines = "\n".join(
        f"- {it['title'] or it['id']}"
        + (f"（{it['region']}{it['subject']}{it['grade']}）" if it.get("region") or it.get("subject") else "")
        for it in slim
    )
    answer = (
        f"题库中匹配到 **{len(slim)}** 份试卷（关键词：{keywords}）。"
        f"请点选下方列表中的一份开始作答：\n\n{lines}\n\n{cand_fence}"
    )
    return {
        "ok": True,
        "handled": True,
        "mode": "take",
        "answer": answer,
        "ui_blocks": [{"type": "exam_candidates", "items": slim}],
        "tool_trace": tool_trace,
        "keywords": keywords,
        "hit_count": len(slim),
    }


def iter_exam_gate_sse(gate: dict[str, Any]) -> list[dict[str, Any]]:
    """Build SSE event dicts for a handled exam gate."""
    events: list[dict[str, Any]] = [
        {"type": "status", "phase": "exam_bank", "answer_mode": "exam_bank"},
    ]
    for row in gate.get("tool_trace") or []:
        events.append(
            {
                "type": "tool_call",
                "tool": row.get("tool") or "search_exam_papers",
                "arguments": row.get("arguments") or {},
            }
        )
        events.append(
            {
                "type": "tool_result",
                "tool": row.get("tool") or "search_exam_papers",
                "output": row.get("output") or "",
                "ok": bool(row.get("ok", True)),
            }
        )
    answer = str(gate.get("answer") or "")
    if answer:
        events.append({"type": "token", "content": answer})
    events.append(
        {
            "type": "done",
            "answer": answer,
            "sources": [],
            "source_refs": [],
            "answer_mode": "exam_bank",
            "rag_architecture": "exam_bank",
            "verified": True,
            "tool_trace": gate.get("tool_trace") or [],
            "ui_blocks": gate.get("ui_blocks") or [],
        }
    )
    return events


def exam_gate_failure_response() -> dict[str, Any]:
    """Structured gate payload when exam_bank lookup throws."""
    return {
        "ok": True,
        "handled": True,
        "mode": "error",
        "answer": (
            "试卷题库服务暂时不可用，请稍后重试，或到 Admin **题库组卷** 页面查看。\n\n"
            "本次不会改用知识库文档作答。"
        ),
        "ui_blocks": [],
        "tool_trace": [],
        "keywords": "",
        "hit_count": 0,
    }
