"""Relationship / org-graph intent routing (deterministic, no LLM)."""

from __future__ import annotations

import re
from typing import Any

_REALTIME_RE = re.compile(
    r"今天|今日|现在|当前|此刻|几点|几月|几号|日期|星期|礼拜|周几|"
    r"北京时间|什么时间|什么时候|哪年|哪一年|哪一月|哪个月|哪天|"
    r"实时|最新|新闻|放假|节假日|调休|天气怎么样|天气如何",
    re.IGNORECASE,
)
_RELATION_GRAPH_RE = re.compile(
    r"关系图|组织图|架构图|汇报关系|上下级|人物关系|谁向谁|组织关系|"
    r"公司关系|人员关系|团队关系|员工关系|组织架构|组织架|管理架构|"
    r"公司架构|深层公司|展示.{0,8}关系|显示.{0,8}关系|看一下.{0,6}关系|"
    r"入库.{0,8}关系|公司.{0,4}关系",
    re.IGNORECASE,
)
_RELATION_TOPIC_RE = re.compile(
    r"关系图|组织图|架构图|上下级|汇报|管辖|CEO|CTO|CFO|COO|"
    r"管理团队|公司关系|深层公司|组织关系|人员关系|员工关系|组织架构",
    re.IGNORECASE,
)
_VIZ_FOLLOWUP_RE = re.compile(
    r"^(展示|显示|看|出|给|来|画|生成|用).{0,6}图|可视化|用图|生成图|出图|"
    r"^图$|关系图$|组织图$",
    re.IGNORECASE,
)


def is_relationship_graph_question(question: str) -> bool:
    q = (question or "").strip()
    return bool(q and _RELATION_GRAPH_RE.search(q))


def is_graph_visual_followup(question: str) -> bool:
    q = (question or "").strip()
    return bool(q and _VIZ_FOLLOWUP_RE.search(q))


def _history_text(history: list[dict[str, Any]] | None, *, lookback: int = 8) -> str:
    if not history:
        return ""
    parts: list[str] = []
    for msg in history[-lookback:]:
        content = str(msg.get("content") or "").strip()
        if content:
            parts.append(content)
    return "\n".join(parts)


def recent_turn_is_relationship_topic(history: list[dict[str, Any]] | None) -> bool:
    if not history:
        return False
    for msg in reversed(history[-8:]):
        content = str(msg.get("content") or "")
        if _RELATION_TOPIC_RE.search(content):
            return True
    return False


def should_use_relationship_graph_fast_path(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> bool:
    """True → skip classic/agentic RAG and call show_relationship_graph directly."""
    q = (question or "").strip()
    if not q:
        return False
    if is_relationship_graph_question(q):
        return True
    if is_graph_visual_followup(q) and recent_turn_is_relationship_topic(history):
        return True
    return False


def resolve_relationship_graph_query(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Build tool query; merge viz follow-up with prior relationship question."""
    q = (question or "").strip()
    if is_relationship_graph_question(q) and not is_graph_visual_followup(q):
        return q
    if history:
        for msg in reversed(history):
            if str(msg.get("role") or "") != "user":
                continue
            prev = str(msg.get("content") or "").strip()
            if not prev or prev == q:
                continue
            if is_relationship_graph_question(prev) or _RELATION_TOPIC_RE.search(prev):
                return f"{prev} {q}".strip()
    hist = _history_text(history)
    if hist and is_graph_visual_followup(q):
        return f"{hist}\n{q}"
    return q


def question_needs_agent_tools(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    if is_relationship_graph_question(q):
        return True
    return bool(_REALTIME_RE.search(q))
