"""Agent 工具 HTTP 接口模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentChatToolPublic(BaseModel):
    id: str
    label: str
    description: str = ""
    enabled: bool = True


class AgentToolsPublic(BaseModel):
    chat_tools_enabled: bool = True
    tools: list[AgentChatToolPublic] = Field(default_factory=list)


class AgentToolsUpdate(BaseModel):
    chat_tools_enabled: bool | None = None
    tools: dict[str, dict[str, Any]] | None = None
