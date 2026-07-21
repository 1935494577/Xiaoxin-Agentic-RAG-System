"""Jnao-compatible channel status API."""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from jnao_harness.gateway.auth import require_admin_user

logger = logging.getLogger(__name__)

_GATEWAY_URL_ENV_KEYS = ("JNAO_HARNESS_GATEWAY_URL", "DEER_FLOW_CHANNELS_GATEWAY_URL")

router = APIRouter(prefix="/api/channels", tags=["channels"])

_ADMIN_REQUIRED_DETAIL = "Admin privileges required to manage channel runtime workers."


class ChannelStatusResponse(BaseModel):
    service_running: bool
    channels: dict[str, dict]


class ChannelRestartResponse(BaseModel):
    success: bool
    message: str


def _harness_gateway_url() -> str | None:
    for key in _GATEWAY_URL_ENV_KEYS:
        value = os.environ.get(key, "").strip().rstrip("/")
        if value:
            return value
    return None


async def _proxy_gateway_channels_status() -> ChannelStatusResponse | None:
    base = _harness_gateway_url()
    if not base:
        return None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base}/api/channels/")
            response.raise_for_status()
            payload = response.json()
    except Exception:
        logger.debug("Harness gateway channel status unavailable at %s", base, exc_info=True)
        return None
    if not isinstance(payload, dict):
        return None
    return ChannelStatusResponse(
        service_running=bool(payload.get("service_running")),
        channels=payload.get("channels") if isinstance(payload.get("channels"), dict) else {},
    )


@router.get("/", response_model=ChannelStatusResponse)
async def get_channels_status() -> ChannelStatusResponse:
    from app.channels.registry import static_channels_status

    try:
        from app.channels.service import get_channel_service
    except ImportError:
        proxied = await _proxy_gateway_channels_status()
        if proxied is not None:
            return proxied
        return ChannelStatusResponse(**static_channels_status())

    service = get_channel_service()
    if service is None:
        proxied = await _proxy_gateway_channels_status()
        if proxied is not None:
            return proxied
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
