"""联网搜索（Tavily Search API）。"""

from __future__ import annotations

import httpx

from config import settings

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def web_search(query: str, max_results: int | None = None) -> str:
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

    payload = {
        "api_key": api_key,
        "query": q,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": limit,
    }

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

    return _format_results(q, data)


def _format_results(query: str, data: dict) -> str:
    lines = [f"搜索「{query}」结果：", ""]

    answer = str(data.get("answer") or "").strip()
    if answer:
        lines.extend([f"【摘要】{answer}", ""])

    results = data.get("results") or []
    if not results and not answer:
        return f"未找到与「{query}」相关的网页结果。"

    for i, row in enumerate(results[:10], start=1):
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "无标题").strip()
        url = str(row.get("url") or "").strip()
        content = str(row.get("content") or "").strip()
        if len(content) > 400:
            content = content[:400].rstrip() + "…"
        lines.append(f"{i}. {title}")
        if content:
            lines.append(f"   {content}")
        if url:
            lines.append(f"   链接: {url}")
        lines.append("")

    return "\n".join(lines).strip()
