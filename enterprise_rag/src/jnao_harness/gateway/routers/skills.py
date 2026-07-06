"""Jnao-compatible skills API (subset: list + enable/disable)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from deerflow.agents.lead_agent.prompt import refresh_skills_system_prompt_cache_async
from deerflow.config.app_config import AppConfig
from deerflow.config.extensions_config import ExtensionsConfig, SkillStateConfig, get_extensions_config, reload_extensions_config
from deerflow.skills import Skill
from deerflow.skills.storage import get_or_new_skill_storage
from deerflow.skills.types import SkillCategory
from jnao_harness.gateway.auth import require_admin_user
from jnao_harness.gateway.deps import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["skills"])

_ADMIN_REQUIRED_DETAIL = "Admin privileges required to manage skills."


class SkillResponse(BaseModel):
    name: str
    description: str
    license: str | None = None
    category: SkillCategory
    enabled: bool = True


class SkillsListResponse(BaseModel):
    skills: list[SkillResponse]


class SkillUpdateRequest(BaseModel):
    enabled: bool


def _skill_to_response(skill: Skill) -> SkillResponse:
    return SkillResponse(
        name=skill.name,
        description=skill.description,
        license=skill.license,
        category=skill.category,
        enabled=skill.enabled,
    )


@router.get("/skills", response_model=SkillsListResponse)
async def list_skills(config: AppConfig = Depends(get_config)) -> SkillsListResponse:
    try:
        skills = get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False)
        return SkillsListResponse(skills=[_skill_to_response(s) for s in skills])
    except Exception as exc:
        logger.error("Failed to load skills", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load skills: {exc}") from exc


@router.put("/skills/{skill_name}", response_model=SkillResponse)
async def update_skill(
    skill_name: str,
    body: SkillUpdateRequest,
    request: Request,
    config: AppConfig = Depends(get_config),
) -> SkillResponse:
    await require_admin_user(request, detail=_ADMIN_REQUIRED_DETAIL)
    skill_name = skill_name.replace("\r\n", "").replace("\n", "")
    skills = get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False)
    if not any(s.name == skill_name for s in skills):
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

    config_path = ExtensionsConfig.resolve_config_path()
    if config_path is None:
        from jnao_harness.paths import repo_root

        config_path = repo_root() / "extensions_config.json"

    extensions_config = get_extensions_config()
    extensions_config.skills[skill_name] = SkillStateConfig(enabled=body.enabled)
    config_data = {
        "mcpServers": {name: server.model_dump() for name, server in extensions_config.mcp_servers.items()},
        "skills": {name: {"enabled": sc.enabled} for name, sc in extensions_config.skills.items()},
    }
    Path(config_path).write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    reload_extensions_config()
    await refresh_skills_system_prompt_cache_async()

    refreshed = get_or_new_skill_storage(app_config=config).load_skills(enabled_only=False)
    updated = next((s for s in refreshed if s.name == skill_name), None)
    if updated is None:
        raise HTTPException(status_code=500, detail=f"Failed to reload skill '{skill_name}'")
    return _skill_to_response(updated)
