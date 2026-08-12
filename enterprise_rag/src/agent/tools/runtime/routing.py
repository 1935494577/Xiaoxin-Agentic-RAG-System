"""Relationship / org-graph intent routing (deterministic, no LLM)."""

from __future__ import annotations

import re
from typing import Any

from retrieval.query_normalize import clean_oral_user_message

_REALTIME_RE = re.compile(
    r"今天|今日|现在|当前|此刻|几点|几月|几号|日期|星期|礼拜|周几|"
    r"北京时间|什么时间|什么时候|哪年|哪一年|哪一月|哪个月|哪天|"
    r"今年|去年|本年|近期|近来|"
    r"实时|最新|新闻|放假|节假日|调休|天气怎么样|天气如何",
    re.IGNORECASE,
)
_WEB_SEARCH_RE = re.compile(
    r"20\d{2}年.*?(?:AI|人工智能|大模型|机器学习|科技|互联网|芯片|半导体)"
    r".*?(?:发展|趋势|动态|热点|进展|突破|回顾|展望|预测|总结|现状|状况)|"
    r"(?:AI|人工智能|大模型|机器学习|科技|互联网|芯片|半导体)"
    r".*?(?:发展|趋势|动态|热点|进展|突破|回顾|展望|预测|现状|状况)|"
    r"(?:发展|趋势|动态|热点|进展|突破|回顾|展望|预测)"
    r".*?(?:AI|人工智能|大模型|机器学习|科技|互联网|芯片|半导体)|"
    r"行业(?:动态|趋势|格局)|市场(?:动态|格局|份额)|"
    r"(?:最新|近期|当前|最近)(?:进展|突破|发布|动态|热点)",
    re.IGNORECASE,
)
_WEATHER_RE = re.compile(
    r"天气|气温|温度|下雨|降雨|下雪|风力|空气质量|几度|冷不冷|热不热|带伞",
    re.IGNORECASE,
)
_TYPHOON_RE = re.compile(
    r"台风|热带风暴|热带低压|气象台|台风路径|登陆点|"
    r"(?:蓝色|黄色|橙色|红色)预警",
    re.IGNORECASE,
)
_CORRECTION_RE = re.compile(
    r"不是已经|搞错了|你错了|说错了|纠正一下|纠正下|"
    r"现在要来的|应该是|才对吧|"
    r"不是.+?[么吗]",
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
_SEARCH_OFFER_RE = re.compile(
    r"上网搜索|联网搜索|帮你搜|帮你查|需要我查|要我查|需要我帮你|帮你找|"
    r"web_search|搜索一下|查一下吗|查吗",
    re.IGNORECASE,
)
_AFFIRMATIVE_RE = re.compile(
    r"^(?:@\S+\s*)*(?:"
    r"需要|"
    r"(?:好的|好|可以|行|嗯|是的|是|要|同意|麻烦|来吧)(?:[,，、\s]*(查|搜)(?:一下)?)?|"
    r"(?:查|搜)(?:一下)?|帮我(?:查|搜)"
    r")[。！？!?\s]*$",
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


def _strip_mention_prefix(question: str) -> str:
    q = (question or "").strip()
    q = re.sub(r"@\S+\s*", "", q).strip()
    q = re.sub(r"^(?:agent|bot)\s+", "", q, flags=re.IGNORECASE).strip()
    return q


def is_web_search_affirmative_followup(question: str) -> bool:
    q = _strip_mention_prefix(question)
    if not q or len(q) > 24:
        return False
    return bool(_AFFIRMATIVE_RE.match(q))


def recent_assistant_offered_web_search(history: list[dict[str, Any]] | None) -> bool:
    if not history:
        return False
    for msg in reversed(history[-6:]):
        if str(msg.get("role") or "") != "assistant":
            continue
        content = str(msg.get("content") or "")
        if _SEARCH_OFFER_RE.search(content):
            return True
    return False


def should_use_web_search_followup(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> bool:
    if not is_web_search_affirmative_followup(question):
        return False
    return recent_assistant_offered_web_search(history)


def resolve_web_search_query(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Merge affirmative follow-up with prior user topic (DeerFlow-style tool context)."""
    q = _strip_mention_prefix(question)
    if not history:
        return q

    prior_user = ""
    for msg in reversed(history):
        role = str(msg.get("role") or "")
        content = str(msg.get("content") or "").strip()
        if role != "user" or not content:
            continue
        if content == q or is_web_search_affirmative_followup(content):
            continue
        prior_user = content
        break

    if prior_user:
        return f"{prior_user} 最新动态与公开信息"

    for msg in reversed(history):
        if str(msg.get("role") or "") != "assistant":
            continue
        snippet = str(msg.get("content") or "").strip()
        if snippet:
            head = snippet.split("\n", 1)[0][:160]
            return f"{head} 联网搜索"
    return q


def normalize_tool_routing_question(question: str) -> str:
    """Alias for routing/tests — same oral cleanup as prepare_turn."""
    return clean_oral_user_message(question)


def is_typhoon_or_warning_question(question: str) -> bool:
    q = normalize_tool_routing_question(question)
    return bool(q and _TYPHOON_RE.search(q))


def is_user_fact_correction(question: str) -> bool:
    q = (question or "").strip()
    return bool(q and _CORRECTION_RE.search(q))


def _extract_corrected_typhoon_name(question: str) -> str | None:
    """从纠错话术中提取纠正后的台风名（修辞：不是X么 → X）。"""
    q = (question or "").strip()
    if not q:
        return None
    # 「不是白海豚么」类修辞肯定
    for m in re.finditer(r"不是\s*([\u4e00-\u9fffA-Za-z]{2,8})\s*[么吗]", q):
        name = m.group(1).strip()
        if any(bad in name for bad in ("已经", "过去", "现在", "这样", "那样")):
            continue
        return name
    # 「应该是白海豚」
    m = re.search(r"(?:应该是|才是|是)\s*[「\"'《]?([\u4e00-\u9fffA-Za-z]{2,8})[」\"'》]?", q)
    if m:
        name = m.group(1).strip()
        if name not in ("已经", "这样") and "过去" not in name:
            # 避免吃到「是萧山」等无关；优先带台风上下文
            if "台风" in q or is_typhoon_or_warning_question(q):
                return name
    names = re.findall(r"台风\s*([\u4e00-\u9fffA-Za-z]{2,8})", q)
    cleaned = [n for n in names if not n.startswith("不是") and "已经" not in n]
    if cleaned:
        return cleaned[-1]
    return None


def resolve_web_search_query_for_correction(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """纠错轮：构造带年份的时效搜索词，优先纠正后的台风名。"""
    from agent.tools.builtins.datetime_cn import beijing_now

    year = beijing_now().year
    name = _extract_corrected_typhoon_name(question)
    if name:
        return f"{year}年台风{name} 最新路径 中央气象台"
    base = resolve_web_search_query(question, history)
    return f"{year}年 {base} 最新核实".strip()


def enrich_question_for_fact_correction(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> str | None:
    """若为事实纠错轮，返回注入核实提示后的 question；否则 None。"""
    q = (question or "").strip()
    if not q or not is_user_fact_correction(q):
        return None
    resolved = resolve_web_search_query_for_correction(q, history)
    return (
        f"{q}\n"
        f"【系统提示】用户在纠正事实：请先直接回应对方纠正点，"
        f"并立即调用 web_search 核实「{resolved}」；"
        f"禁止复述上轮错误事实，禁止解释无关工具故障。"
    )


def question_needs_realtime_tools(question: str) -> bool:
    q = normalize_tool_routing_question(question)
    if not q or is_relationship_graph_question(q):
        return False
    if is_typhoon_or_warning_question(q):
        return True
    if is_user_fact_correction(q):
        return True
    if _WEATHER_RE.search(q):
        return True
    if _WEB_SEARCH_RE.search(q):
        return True
    return bool(_REALTIME_RE.search(q))


def question_needs_agent_tools(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    if is_relationship_graph_question(q):
        return True
    return question_needs_realtime_tools(q)
