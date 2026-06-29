"""Agent 工具配置 API（独立于 main 路由定义）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from agent.tools.api.schemas import AgentToolsPublic, AgentToolsUpdate
from agent.tools.config.registry import public_tools_config, save_tools_config

router = APIRouter(tags=["agent-tools"])


@router.get("/config/agent-tools", response_model=AgentToolsPublic)
def get_agent_tools_config(request: Request):
    from account_config.store import effective_agent_tools
    from account_config.request_auth import resolve_config_actor

    user_id, _can_write = resolve_config_actor(request)
    return AgentToolsPublic.model_validate(effective_agent_tools(user_id))


@router.put("/config/agent-tools", response_model=AgentToolsPublic)
def update_agent_tools_config(body: AgentToolsUpdate, request: Request):
    from account_config.store import effective_agent_tools, save_platform_scope, save_user_scope_patch
    from account_config.request_auth import resolve_config_actor

    user_id, can_write = resolve_config_actor(request)
    patch = body.model_dump(exclude_unset=True)
    if patch:
        if can_write:
            save_tools_config(patch)
            save_platform_scope("agent_tools", updated_by=user_id or "")
        elif user_id:
            save_user_scope_patch(user_id, "agent_tools", patch)
        else:
            raise HTTPException(status_code=401, detail="登录后才能保存个人配置")
    return AgentToolsPublic.model_validate(effective_agent_tools(user_id))
