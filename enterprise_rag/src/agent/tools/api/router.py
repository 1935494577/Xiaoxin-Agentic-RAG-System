"""Agent 工具配置 API（独立于 main 路由定义）。"""

from __future__ import annotations

from fastapi import APIRouter

from agent.tools.api.schemas import AgentToolsPublic, AgentToolsUpdate
from agent.tools.config.registry import public_tools_config, save_tools_config

router = APIRouter(tags=["agent-tools"])


@router.get("/config/agent-tools", response_model=AgentToolsPublic)
def get_agent_tools_config():
    return AgentToolsPublic.model_validate(public_tools_config())


@router.put("/config/agent-tools", response_model=AgentToolsPublic)
def update_agent_tools_config(body: AgentToolsUpdate):
    patch = body.model_dump(exclude_unset=True)
    save_tools_config(patch)
    return AgentToolsPublic.model_validate(public_tools_config())
