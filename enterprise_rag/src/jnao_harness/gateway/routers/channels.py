"""Jnao-compatible channel status API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from jnao_harness.gateway.auth import require_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["channels"])

_ADMIN_REQUIRED_DETAIL = "Admin privileges required to manage channel runtime workers."


class ChannelStatusResponse(BaseModel):
    service_running: bool
    channels: dict[str, dict]


class ChannelRestartResponse(BaseModel):
    success: bool
    message: str


@router.get("/", response_model=ChannelStatusResponse)
async def get_channels_status() -> ChannelStatusResponse:
    from app.channels.registry import static_channels_status

    try:
        from app.channels.service import get_channel_service
    except ImportError:
        return ChannelStatusResponse(**static_channels_status())

    service = get_channel_service()
    if service is None:
        return ChannelStatusResponse(**static_channels_status())
    status = service.get_status()
    return ChannelStatusResponse(**status)


@router.post("/{name}/restart", response_model=ChannelRestartResponse)
async def restart_channel(name: str, request: Request) -> ChannelRestartResponse:
    await require_admin_user(request, detail=_ADMIN_REQUIRED_DETAIL)

    from app.channels.service import get_channel_service

    service = get_channel_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Channel service is not running")

    success = await service.restart_channel(name)
    if success:
        logger.info("Channel %s restarted", name)
        return ChannelRestartResponse(success=True, message=f"Channel {name} restarted successfully")
    return ChannelRestartResponse(success=False, message=f"Failed to restart channel {name}")
