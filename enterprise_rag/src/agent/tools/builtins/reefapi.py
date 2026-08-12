"""ReefAPI 实时网页结构化数据（对应 reefapi-mcp 的 discovery + call_engine）。

走官方 REST：GET /catalog（发现）；POST /{engine}/v1/{action}（执行，需 Key）。
文档：https://reefapi.com/mcp
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from config import settings

_STOP = {
    "a", "an", "the", "what", "which", "is", "are", "to", "of", "for", "with", "on",
    "in", "at", "and", "or", "find", "get", "show", "list", "search", "data", "api",
    "查", "搜索", "一下", "帮我", "什么", "怎么", "如何",
}


def _base() -> str:
    return (settings.reefapi_base or "https://api.reefapi.com").rstrip("/")


def _key() -> str:
    return (settings.reefapi_key or "").strip()


def _timeout() -> float:
    return float(max(3, int(settings.reefapi_timeout_seconds or 60)))


def _tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9\u4e00-\u9fff]+", (s or "").lower()) if len(t) >= 2 and t not in _STOP]


def _fetch_catalog() -> dict[str, Any]:
    with httpx.Client(base_url=_base(), timeout=_timeout()) as client:
        r = client.get("/catalog")
        r.raise_for_status()
        return r.json()


def _format_json(data: Any, *, limit: int = 12000) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > limit:
        return text[:limit].rstrip() + f"\n…（已截断，原长 {len(text)} 字）"
    return text


def reefapi_search(query: str = "", engine: str = "") -> str:
    """发现引擎：空 query 列目录摘要；有 query 按关键词排序；指定 engine 返回该引擎 actions。"""
    try:
        cat = _fetch_catalog()
    except httpx.TimeoutException:
        return "ReefAPI 目录请求超时，请稍后重试。"
    except httpx.HTTPError as e:
        return f"ReefAPI 目录不可用：{e}"

    engines = cat.get("engines") or []
    if not isinstance(engines, list):
        return "ReefAPI 目录格式异常。"

    eng = (engine or "").strip()
    if eng:
        for e in engines:
            if not isinstance(e, dict):
                continue
            if str(e.get("name") or "") == eng:
                actions = []
                for a in e.get("actions") or []:
                    if not isinstance(a, dict):
                        continue
                    actions.append(
                        {
                            "action": a.get("name"),
                            "description": a.get("description"),
                            "required_params": list(a.get("required_params") or []),
                            "optional_params": list(a.get("optional_params") or [])[:12],
                            "example_params": a.get("example_params"),
                        }
                    )
                out = {
                    "engine": e.get("name"),
                    "title": e.get("title"),
                    "category": (e.get("category") or {}).get("title", ""),
                    "action_count": len(actions),
                    "actions": actions,
                    "next": "调用 reefapi_call(engine, action, params)；params 用 JSON 对象。",
                }
                return _format_json(out)
        names = [str(e.get("name")) for e in engines if isinstance(e, dict) and e.get("name")]
        return _format_json({"error": f"未知引擎 '{eng}'", "hint": "先 reefapi_search 查引擎名", "sample": names[:40]})

    q = (query or "").strip()
    qtokens = _tokens(q)
    scored: list[tuple[int, dict[str, Any]]] = []
    for e in engines:
        if not isinstance(e, dict):
            continue
        cat_title = (e.get("category") or {}).get("title", "")
        actions = e.get("actions") or []
        action_text = " ".join(
            f"{a.get('name', '')} {a.get('description', '')}" for a in actions if isinstance(a, dict)
        )
        hay = f"{e.get('name', '')} {e.get('title', '')} {cat_title} {action_text}".lower()
        if not qtokens:
            score = 1
        else:
            score = sum(1 for t in qtokens if t in hay)
            if score <= 0:
                continue
        scored.append(
            (
                score,
                {
                    "engine": e.get("name"),
                    "title": e.get("title"),
                    "category": cat_title,
                    "actions": [a.get("name") for a in actions if isinstance(a, dict)][:16],
                    "match": score,
                },
            )
        )

    scored.sort(key=lambda x: (-x[0], str(x[1].get("engine") or "")))
    rows = [row for _, row in scored[:12]]
    if not rows and q:
        return (
            f"未匹配到与「{q}」相关的引擎。可改用英文关键词（如 amazon reviews、domain availability），"
            "或 reefapi_search(query=\"\") 浏览目录后再 reefapi_search(engine=\"名称\")。"
        )
    return _format_json(
        {
            "count": len(rows),
            "query": q,
            "engines": rows,
            "next": "选中 engine 后 reefapi_search(engine=...) 看参数，再 reefapi_call。",
            "engine_count_total": cat.get("engine_count") or len(engines),
        }
    )


def _parse_params(params: Any) -> dict[str, Any] | str:
    if params is None or params == "":
        return {}
    if isinstance(params, dict):
        return params
    if isinstance(params, str):
        text = params.strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return "params 必须是 JSON 对象字符串，例如 {\"asin\":\"B0C123\",\"domain\":\"com\"}"
        if not isinstance(data, dict):
            return "params JSON 必须是对象（键值对）。"
        return data
    return "params 类型无效，请传对象或 JSON 字符串。"


def reefapi_call(engine: str, action: str, params: Any = None) -> str:
    """执行某引擎 action，返回 {ok, data, meta, error} 文本。"""
    eng = (engine or "").strip()
    act = (action or "").strip()
    if not eng or not act:
        return "请提供 engine 与 action（可先 reefapi_search 发现）。"

    key = _key()
    if not key:
        return "ReefAPI 未配置：请在 .env 中设置 REEFAPI_KEY（https://reefapi.com）。"

    parsed = _parse_params(params)
    if isinstance(parsed, str):
        return parsed

    try:
        with httpx.Client(
            base_url=_base(),
            timeout=_timeout(),
            headers={"x-api-key": key},
        ) as client:
            r = client.post(f"/{eng}/v1/{act}", json=parsed)
            try:
                body = r.json()
            except Exception:
                return f"HTTP {r.status_code}：{r.text[:800]}"
            if r.status_code >= 400 and isinstance(body, dict) and not body.get("ok", True):
                return _format_json(body)
            if r.status_code >= 400:
                return _format_json({"ok": False, "http_status": r.status_code, "body": body})
            return _format_json(body)
    except httpx.TimeoutException:
        return "ReefAPI 调用超时，请稍后重试。"
    except httpx.HTTPError as e:
        return f"ReefAPI 调用失败：{e}"
