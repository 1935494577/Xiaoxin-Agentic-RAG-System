"""内置工具实现（按工具拆文件，在此统一调度）。"""

from __future__ import annotations

from typing import Any

from agent.tools.builtins.datetime_cn import get_beijing_time
from agent.tools.builtins.weather import get_weather
from agent.tools.builtins.web_search import web_search


def run_builtin(tool_id: str, arguments: dict[str, Any]) -> str:
    if tool_id == "get_beijing_time":
        return get_beijing_time()
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


__all__ = ["get_beijing_time", "get_weather", "web_search", "run_builtin"]
