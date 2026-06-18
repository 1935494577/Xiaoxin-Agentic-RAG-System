"""内置工具实现（按工具拆文件，在此统一调度）。"""

from __future__ import annotations

from typing import Any

from agent.tools.builtins.datetime_cn import get_beijing_time
from agent.tools.builtins.kb_search import get_kb_hits, kb_search, set_kb_search_context
from agent.tools.builtins.relationship_graph import (
    clear_relationship_graph_context,
    set_relationship_graph_context,
    show_relationship_graph,
)
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
        return web_search(str(arguments.get("query") or ""), max_results=mr)
    return f"未知工具：{tool_id}"


__all__ = [
    "get_beijing_time",
    "get_weather",
    "web_search",
    "kb_search",
    "show_relationship_graph",
    "run_builtin",
]
