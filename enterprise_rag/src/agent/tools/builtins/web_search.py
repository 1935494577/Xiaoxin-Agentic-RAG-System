"""联网搜索（Tavily Search API）。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import httpx

from config import settings

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

DEFAULT_TIMELINESS_DAYS = 3

# 台风/预警等优先权威站，降低旧闻混入
AUTHORITATIVE_WEATHER_DOMAINS: tuple[str, ...] = (
    "nmc.cn",
    "weather.com.cn",
    "cma.gov.cn",
    "www.cma.gov.cn",
    "typhoon.nmc.cn",
    "news.cn",
    "xinhuanet.com",
    "people.com.cn",
)

_TIMELINESS_RE = re.compile(
    r"台风|热带风暴|热带低压|气象台|预警|路径|登陆|"
    r"最新|实时|今天|今日|当前|现在|近期|正在|"
    r"新闻|股价|放假|调休|节假日",
    re.IGNORECASE,
)


def looks_like_timeliness_query(query: str) -> bool:
    q = (query or "").strip()
    return bool(q and _TIMELINESS_RE.search(q))


def _clamp_days(days: int | None) -> int | None:
    if days is None:
        return None
    try:
        d = int(days)
    except (TypeError, ValueError):
        return None
    return max(1, min(d, 30))


def _parse_published_date(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    m = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", text)
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
    except ValueError:
        return None


def _is_stale(published: datetime | None, days: int) -> bool:
    if published is None:
        return False  # 无日期时保留，由摘要侧提示
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return published < cutoff


def web_search(
    query: str,
    max_results: int | None = None,
    days: int | None = None,
    include_domains: Sequence[str] | None = None,
) -> str:
    q = (query or "").strip()
    if not q:
        return "请提供搜索关键词。"
    if len(q) > 512:
        return "搜索关键词过长（最多 512 字）。"

    api_key = (settings.tavily_api_key or "").strip()
    if not api_key:
        return "联网搜索未配置：请在 .env 中设置 TAVILY_API_KEY（https://tavily.com）。"

    limit = max_results if max_results is not None else settings.web_search_max_results
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = settings.web_search_max_results
    limit = max(1, min(limit, 10))

    effective_days = _clamp_days(days)
    if effective_days is None and looks_like_timeliness_query(q):
        effective_days = DEFAULT_TIMELINESS_DAYS

    domains: list[str] = []
    if include_domains:
        domains = [str(d).strip() for d in include_domains if str(d).strip()]
    elif looks_like_timeliness_query(q) and re.search(r"台风|气象|预警|路径|天气", q):
        domains = list(AUTHORITATIVE_WEATHER_DOMAINS)

    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": q,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": limit,
    }
    if effective_days is not None:
        payload["days"] = effective_days
    if domains:
        payload["include_domains"] = domains

    timeout = max(3, int(settings.web_search_timeout_seconds))
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(TAVILY_SEARCH_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        return "联网搜索超时，请稍后重试。"
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in (401, 403):
            return "Tavily API Key 无效或未授权，请检查 .env 中的 TAVILY_API_KEY。"
        return f"联网搜索失败（HTTP {code}）。"
    except httpx.HTTPError as e:
        return f"联网搜索暂时不可用：{e}"

    return _format_results(q, data, freshness_days=effective_days)


def _format_results(query: str, data: dict, *, freshness_days: int | None = None) -> str:
    lines = [f"搜索「{query}」结果：", ""]
    if freshness_days is not None:
        lines.append(f"【时效窗口】近 {freshness_days} 天（更早来源已过滤或标注可能过时）")
        lines.append("")

    answer = str(data.get("answer") or "").strip()
    if answer:
        lines.extend([f"【摘要】{answer}", ""])

    results = data.get("results") or []
    if not results and not answer:
        return f"未找到与「{query}」相关的网页结果。"

    kept = 0
    for i, row in enumerate(results[:10], start=1):
        if not isinstance(row, dict):
            continue
        published_raw = row.get("published_date") or row.get("date")
        published = _parse_published_date(published_raw)
        stale = bool(freshness_days and _is_stale(published, freshness_days))
        if stale:
            # 明确过旧：跳过正文，避免模型当现行事实
            continue

        title = str(row.get("title") or "无标题").strip()
        url = str(row.get("url") or "").strip()
        content = str(row.get("content") or "").strip()
        if len(content) > 400:
            content = content[:400].rstrip() + "…"
        kept += 1
        lines.append(f"{kept}. {title}")
        if content:
            lines.append(f"   {content}")
        if url:
            lines.append(f"   链接: {url}")
        if published_raw:
            lines.append(f"   发布: {published_raw}")
        lines.append("")

    if kept == 0 and answer:
        # 摘要仍可用，但提醒无新鲜条目
        lines.append("（无符合时效窗口的网页条目，请谨慎对待摘要）")
    elif kept == 0 and not answer:
        return f"未找到近 {freshness_days or DEFAULT_TIMELINESS_DAYS} 天内与「{query}」相关的网页结果。"

    return "\n".join(lines).strip()
