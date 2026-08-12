"""内置工具实现（按工具拆文件，在此统一调度）。"""

from __future__ import annotations

from typing import Any

from agent.tools.builtins.datetime_cn import get_beijing_time
from agent.tools.builtins.format_structured_output import format_structured_output
from agent.tools.builtins.kb_search import get_kb_hits, kb_search, set_kb_search_context
from agent.tools.builtins.list_kb_sources import list_kb_sources
from agent.tools.builtins.relationship_graph import (
    clear_relationship_graph_context,
    set_relationship_graph_context,
    show_relationship_graph,
)
from agent.tools.builtins.reefapi import reefapi_call, reefapi_search
from agent.tools.builtins.weather import get_weather
from agent.tools.builtins.web_search import web_search


def run_builtin(tool_id: str, arguments: dict[str, Any]) -> str:
    if tool_id == "get_beijing_time":
        return get_beijing_time()
    if tool_id == "kb_search":
        tk: int | None = None
        raw_tk = arguments.get("top_k")
        if raw_tk is not None:
            try:
                tk = int(raw_tk)
            except (TypeError, ValueError):
                tk = None
        return kb_search(str(arguments.get("query") or ""), top_k=tk)
    if tool_id == "show_relationship_graph":
        hops: int | None = None
        raw_hops = arguments.get("max_hops")
        if raw_hops is not None:
            try:
                hops = int(raw_hops)
            except (TypeError, ValueError):
                hops = None
        return show_relationship_graph(
            str(arguments.get("query") or ""),
            center_name=str(arguments.get("center_name") or "") or None,
            max_hops=hops,
        )
    if tool_id == "get_weather":
        fh: int | None = None
        raw_fh = arguments.get("forecast_hours")
        if raw_fh is not None:
            try:
                fh = int(raw_fh)
            except (TypeError, ValueError):
                fh = None
        return get_weather(str(arguments.get("city") or ""), forecast_hours=fh)
    if tool_id == "web_search":
        mr: int | None = None
        raw_mr = arguments.get("max_results")
        if raw_mr is not None:
            try:
                mr = int(raw_mr)
            except (TypeError, ValueError):
                mr = None
        days: int | None = None
        raw_days = arguments.get("days")
        if raw_days is not None:
            try:
                days = int(raw_days)
            except (TypeError, ValueError):
                days = None
        domains_raw = arguments.get("include_domains")
        domains: list[str] | None = None
        if isinstance(domains_raw, str) and domains_raw.strip():
            domains = [p.strip() for p in domains_raw.split(",") if p.strip()]
        elif isinstance(domains_raw, (list, tuple)):
            domains = [str(p).strip() for p in domains_raw if str(p).strip()]
        return web_search(
            str(arguments.get("query") or ""),
            max_results=mr,
            days=days,
            include_domains=domains,
        )
    if tool_id == "reefapi_search":
        return reefapi_search(
            query=str(arguments.get("query") or ""),
            engine=str(arguments.get("engine") or ""),
        )
    if tool_id == "reefapi_call":
        return reefapi_call(
            str(arguments.get("engine") or ""),
            str(arguments.get("action") or ""),
            arguments.get("params"),
        )
    if tool_id == "list_kb_sources":
        lim: int | None = None
        raw_lim = arguments.get("limit")
        if raw_lim is not None:
            try:
                lim = int(raw_lim)
            except (TypeError, ValueError):
                lim = None
        return list_kb_sources(limit=lim if lim is not None else 30)
    if tool_id == "format_structured_output":
        return format_structured_output(
            str(arguments.get("content") or ""),
            str(arguments.get("schema_id") or ""),
        )
    return f"未知工具：{tool_id}"


__all__ = [
    "get_beijing_time",
    "get_weather",
    "web_search",
    "reefapi_search",
    "reefapi_call",
    "kb_search",
    "show_relationship_graph",
    "run_builtin",
]
