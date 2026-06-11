"""内置工具实现（按工具拆文件，在此统一调度）。"""

from __future__ import annotations

from typing import Any

from agent.tools.builtins.weather import get_weather


def run_builtin(tool_id: str, arguments: dict[str, Any]) -> str:
    if tool_id == "get_weather":
        return get_weather(str(arguments.get("city") or ""))
    return f"未知工具：{tool_id}"


__all__ = ["get_weather", "run_builtin"]
