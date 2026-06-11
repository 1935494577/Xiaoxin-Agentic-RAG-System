"""对话 Agent 工具包（与入库 processing 工具独立）。

分层：
- config/   配置持久化与工具注册表
- protocol/ OpenAI function-calling 协议
- runtime/  执行循环与 Chat 流式集成
- builtins/ 内置工具实现
- api/      HTTP 配置接口（供 FastAPI include_router）
"""

from agent.tools.config.registry import (
    enabled_tool_ids,
    execute_tool,
    load_tools_config,
    public_tools_config,
    save_tools_config,
)
from agent.tools.runtime.stream import is_tools_active, stream_general_answer

__all__ = [
    "enabled_tool_ids",
    "execute_tool",
    "is_tools_active",
    "load_tools_config",
    "public_tools_config",
    "save_tools_config",
    "stream_general_answer",
]
