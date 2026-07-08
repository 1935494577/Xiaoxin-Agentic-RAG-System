"""DeerFlow-style channel provider config API (admin runtime credentials)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.channels.runtime_config_store import ChannelRuntimeConfigStore
from jnao_harness.channels_config import (
    connections_config_shim,
    is_connections_enabled,
    is_provider_enabled,
    merge_channels_config,
)
from jnao_harness.gateway.auth import require_admin_user
from jnao_harness.gateway.gateway_client import harness_gateway_url, proxy_gateway_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["channel-connections"])

_MASKED = "********"
_ADMIN_DETAIL = "Admin privileges required to manage channel runtime credentials."
_STATE_TTL_SECONDS = 600

_PROVIDER_META: dict[str, dict[str, str]] = {
    "telegram": {"display_name": "Telegram", "auth_mode": "deep_link"},
    "slack": {"display_name": "Slack", "auth_mode": "binding_code"},
    "discord": {"display_name": "Discord", "auth_mode": "binding_code"},
    "feishu": {"display_name": "Feishu", "auth_mode": "binding_code"},
    "dingtalk": {"display_name": "DingTalk", "auth_mode": "binding_code"},
    "wechat": {"display_name": "WeChat", "auth_mode": "binding_code"},
    "wecom": {"display_name": "WeCom", "auth_mode": "binding_code"},
}

_CREDENTIAL_FIELDS: dict[str, tuple[dict[str, str], ...]] = {
    "telegram": (
        {"name": "bot_token", "label": "Bot token", "type": "password"},
        {"name": "bot_username", "label": "Bot username", "type": "text"},
    ),
    "slack": (
        {"name": "bot_token", "label": "Bot token", "type": "password"},
        {"name": "app_token", "label": "App token", "type": "password"},
    ),
    "discord": ({"name": "bot_token", "label": "Bot token", "type": "password"},),
    "feishu": (
        {"name": "app_id", "label": "App ID", "type": "text"},
        {"name": "app_secret", "label": "App secret", "type": "password"},
    ),
    "dingtalk": (
        {"name": "client_id", "label": "Client ID", "type": "text"},
        {"name": "client_secret", "label": "Client secret", "type": "password"},
    ),
    "wechat": ({"name": "bot_token", "label": "Bot token", "type": "password"},),
    "wecom": (
        {"name": "bot_id", "label": "Bot ID", "type": "text"},
        {"name": "bot_secret", "label": "Bot secret", "type": "password"},
    ),
}

_RUNTIME_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "telegram": ("bot_token",),
    "slack": ("bot_token", "app_token"),
    "discord": ("bot_token",),
    "feishu": ("app_id", "app_secret"),
    "dingtalk": ("client_id", "client_secret"),
    "wechat": ("bot_token",),
    "wecom": ("bot_id", "bot_secret"),
}


class ChannelCredentialFieldResponse(BaseModel):
    name: str
    label: str
    type: str = "text"
    required: bool = True


class ChannelProviderResponse(BaseModel):
    provider: str
    display_name: str
    enabled: bool
    configured: bool
    connectable: bool
    unavailable_reason: str | None = None
    auth_mode: str
    connection_status: str
    credential_fields: list[ChannelCredentialFieldResponse] = Field(default_factory=list)
    credential_values: dict[str, str] = Field(default_factory=dict)


class ChannelProvidersResponse(BaseModel):
    enabled: bool
    providers: list[ChannelProviderResponse]


class ChannelConnectResponse(BaseModel):
    provider: str
    mode: str
    url: str | None = None
    code: str
    instruction: str
    expires_in: int


class ChannelConnectionResponse(BaseModel):
    id: str
    provider: str
    status: str
    external_account_id: str | None = None
    external_account_name: str | None = None
    workspace_id: str | None = None
    workspace_name: str | None = None


class ChannelConnectionsResponse(BaseModel):
    connections: list[ChannelConnectionResponse]


class ChannelRuntimeConfigRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


async def _runtime_store(request: Request) -> ChannelRuntimeConfigStore:
    store = getattr(request.app.state, "channel_runtime_config_store", None)
    if isinstance(store, ChannelRuntimeConfigStore):
        return store
    store = await asyncio.to_thread(ChannelRuntimeConfigStore)
    request.app.state.channel_runtime_config_store = store
    return store


async def _channels_config(request: Request) -> dict[str, Any]:
    cached = getattr(request.app.state, "channels_config", None)
    if isinstance(cached, dict):
        return cached
    merged = merge_channels_config({})
    request.app.state.channels_config = merged
    return merged


def _credential_fields(provider: str) -> list[ChannelCredentialFieldResponse]:
    fields = _CREDENTIAL_FIELDS.get(provider)
    if fields is None:
        raise HTTPException(status_code=404, detail="Unknown channel provider")
    return [ChannelCredentialFieldResponse(**field) for field in fields]


def _runtime_configured(provider: str, channels_config: dict[str, Any]) -> bool:
    runtime = channels_config.get(provider)
    if not isinstance(runtime, dict) or not runtime.get("enabled", False):
        return False
    return all(str(runtime.get(key) or "").strip() for key in _RUNTIME_REQUIREMENTS[provider])


async def _gateway_channel_status() -> dict[str, Any] | None:
    payload = await proxy_gateway_json("GET", "/api/channels/")
    return payload if isinstance(payload, dict) else None


def _gateway_provider_running(provider: str, status: dict[str, Any] | None) -> bool | None:
    if not isinstance(status, dict):
        return None
    if not status.get("service_running"):
        return False
    channel = status.get("channels", {}).get(provider)
    if not isinstance(channel, dict):
        return None
    return bool(channel.get("running"))


def _runtime_running(provider: str) -> bool | None:
    try:
        from app.channels.service import get_channel_service
    except ImportError:
        return None
    service = get_channel_service()
    if service is None:
        return None
    status = service.get_status()
    if not status.get("service_running"):
        return False
    channel = status.get("channels", {}).get(provider)
    if not isinstance(channel, dict):
        return None
    return bool(channel.get("running"))


def _connect_instruction(provider: str, code: str) -> str:
    meta = _PROVIDER_META.get(provider, {})
    display_name = meta.get("display_name", provider)
    if provider == "telegram":
        return f"向 {display_name} 机器人发送：/start {code}"
    return f"向 {display_name} 机器人发送：/connect {code}"


async def _gateway_connect_response(provider: str) -> ChannelConnectResponse | None:
    payload = await proxy_gateway_json("POST", f"/api/channels/{provider}/connect")
    if payload is None:
        return None
    code = str(payload.get("code") or "").strip()
    if not code:
        return None
    return ChannelConnectResponse(
        provider=provider,
        mode=str(payload.get("mode") or _PROVIDER_META[provider]["auth_mode"]),
        url=payload.get("url"),
        code=code,
        instruction=_connect_instruction(provider, code),
        expires_in=int(payload.get("expires_in") or _STATE_TTL_SECONDS),
    )


def _provider_response(
    provider: str,
    channels_config: dict[str, Any],
    *,
    connection_status: str | None = None,
) -> ChannelProviderResponse:
    meta = _PROVIDER_META[provider]
    enabled = is_provider_enabled(provider)
    configured = enabled and _runtime_configured(provider, channels_config)
    unavailable: str | None = None
    if enabled and not configured:
        unavailable = f"请填写 {meta['display_name']} 所需凭证。"
    elif configured and _runtime_running(provider) is False:
        unavailable = f"{meta['display_name']} 已配置但未运行（需 harness API 启动 channel worker）。"
    credential_values: dict[str, str] = {}
    runtime = channels_config.get(provider)
    if isinstance(runtime, dict):
        for field in _credential_fields(provider):
            value = str(runtime.get(field.name) or "").strip()
            if not value:
                continue
            credential_values[field.name] = _MASKED if field.type == "password" else value
    resolved_status = connection_status
    if resolved_status is None:
        if configured and _runtime_running(provider):
            resolved_status = "not_connected"
        else:
            resolved_status = "not_connected"
    return ChannelProviderResponse(
        provider=provider,
        display_name=meta["display_name"],
        enabled=enabled,
        configured=configured,
        connectable=configured and unavailable is None,
        unavailable_reason=unavailable,
        auth_mode=meta["auth_mode"],
        connection_status=resolved_status,
        credential_fields=_credential_fields(provider),
        credential_values=credential_values,
    )


def _required_values(
    provider: str,
    values: dict[str, str],
    existing: dict[str, Any] | None = None,
) -> dict[str, str]:
    existing = existing or {}
    cleaned: dict[str, str] = {}
    missing: list[str] = []
    for field in _credential_fields(provider):
        raw = values.get(field.name, "")
        if field.type == "password" and raw == _MASKED:
            prev = str(existing.get(field.name) or "").strip()
            if prev:
                cleaned[field.name] = prev
                continue
        value = raw.strip() if isinstance(raw, str) else str(raw or "").strip()
        if field.required and not value:
            missing.append(field.label)
        cleaned[field.name] = value
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少必填项：{', '.join(missing)}")
    return cleaned


async def _apply_runtime_channel(provider: str, runtime_config: dict[str, Any]) -> bool | None:
    try:
        from app.channels.service import get_channel_service
    except ImportError:
        return None
    service = get_channel_service()
    if service is None:
        return None
    try:
        return await service.configure_channel(provider, runtime_config)
    except Exception:
        logger.exception("Failed to apply runtime channel config for %s", provider)
        return False


@router.get("/connections", response_model=ChannelConnectionsResponse)
async def get_channel_connections(request: Request) -> ChannelConnectionsResponse:
    payload = await proxy_gateway_json("GET", "/api/channels/connections")
    if isinstance(payload, dict):
        rows = payload.get("connections")
        if isinstance(rows, list):
            connections = [ChannelConnectionResponse(**row) for row in rows if isinstance(row, dict)]
            return ChannelConnectionsResponse(connections=connections)
    return ChannelConnectionsResponse(connections=[])


@router.post("/{provider}/connect", response_model=ChannelConnectResponse)
async def connect_channel_provider(provider: str, request: Request) -> ChannelConnectResponse:
    if provider not in _PROVIDER_META:
        raise HTTPException(status_code=404, detail="Unknown channel provider")
    if not is_connections_enabled():
        raise HTTPException(status_code=400, detail="Channel connections are disabled")
    if not is_provider_enabled(provider):
        raise HTTPException(status_code=400, detail="Channel provider is not enabled")

    channels_config = await _channels_config(request)
    if not _runtime_configured(provider, channels_config):
        raise HTTPException(status_code=400, detail="请先保存机器人凭证")
    if _runtime_running(provider) is False:
        raise HTTPException(
            status_code=400,
            detail=f"{_PROVIDER_META[provider]['display_name']} 已配置但未运行，请确认 Harness Gateway (8011) 已启动。",
        )
    gateway_status = await _gateway_channel_status()
    gateway_running = _gateway_provider_running(provider, gateway_status)
    if gateway_running is False:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{_PROVIDER_META[provider]['display_name']} Worker 未运行，"
                "请检查 Bot 凭证与网络（需能访问 wss://openws.work.weixin.qq.com）。"
            ),
        )

    proxied = await _gateway_connect_response(provider)
    if proxied is not None:
        return proxied

    if not harness_gateway_url():
        raise HTTPException(
            status_code=503,
            detail="Harness Gateway 未配置。请使用 run-dev-harness.ps1 启动 8011 服务。",
        )
    raise HTTPException(
        status_code=503,
        detail="无法从 Harness Gateway 获取绑定码，请确认 8011 服务正在运行。",
    )


@router.get("/providers", response_model=ChannelProvidersResponse)
async def get_channel_providers(request: Request) -> ChannelProvidersResponse:
    enabled = is_connections_enabled()
    channels_config = await _channels_config(request)
    connected_providers: set[str] = set()
    payload = await proxy_gateway_json("GET", "/api/channels/connections")
    if isinstance(payload, dict):
        rows = payload.get("connections")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("status") == "connected" and row.get("provider"):
                    connected_providers.add(str(row["provider"]))

    providers: list[ChannelProviderResponse] = []
    for provider in _PROVIDER_META:
        if not is_provider_enabled(provider):
            continue
        configured = _runtime_configured(provider, channels_config)
        running = _runtime_running(provider)
        status = "not_connected"
        if configured and running and provider in connected_providers:
            status = "connected"
        providers.append(_provider_response(provider, channels_config, connection_status=status))
    return ChannelProvidersResponse(enabled=enabled, providers=providers)


@router.post("/{provider}/runtime-config", response_model=ChannelProviderResponse)
async def configure_channel_provider_runtime(
    provider: str,
    body: ChannelRuntimeConfigRequest,
    request: Request,
) -> ChannelProviderResponse:
    await require_admin_user(request, detail=_ADMIN_DETAIL)
    if provider not in _PROVIDER_META:
        raise HTTPException(status_code=404, detail="Unknown channel provider")
    if not is_connections_enabled():
        raise HTTPException(status_code=400, detail="Channel connections are disabled")
    if not is_provider_enabled(provider):
        raise HTTPException(status_code=400, detail="Channel provider is not enabled")

    channels_config = await _channels_config(request)
    existing = channels_config.get(provider)
    runtime_config = dict(existing) if isinstance(existing, dict) else {}
    values = _required_values(provider, body.values, runtime_config)
    runtime_config["enabled"] = True
    for key in _RUNTIME_REQUIREMENTS[provider]:
        runtime_config[key] = values[key]
    if provider == "telegram":
        runtime_config["bot_username"] = values.get("bot_username", "")

    started = await _apply_runtime_channel(provider, runtime_config)
    if started is False:
        raise HTTPException(status_code=400, detail=f"无法启动 {_PROVIDER_META[provider]['display_name']}，请检查凭证。")

    store = await _runtime_store(request)
    await asyncio.to_thread(store.set_provider_config, provider, runtime_config)

    live = await _channels_config(request)
    live[provider] = runtime_config
    request.app.state.channels_config = live

    await proxy_gateway_json(
        "POST",
        f"/api/channels/{provider}/runtime-config",
        json={"values": values if provider != "telegram" else {**values, "bot_username": runtime_config.get("bot_username", "")}},
    )

    return _provider_response(provider, live)


@router.delete("/{provider}/runtime-config", response_model=ChannelProviderResponse)
async def disconnect_channel_provider_runtime(provider: str, request: Request) -> ChannelProviderResponse:
    await require_admin_user(request, detail=_ADMIN_DETAIL)
    if provider not in _PROVIDER_META:
        raise HTTPException(status_code=404, detail="Unknown channel provider")

    live = await _channels_config(request)
    candidate = dict(live)
    candidate.pop(provider, None)
    try:
        from app.channels.service import get_channel_service

        service = get_channel_service()
        if service is not None:
            await service.remove_channel(provider)
    except ImportError:
        pass

    store = await _runtime_store(request)
    await asyncio.to_thread(store.set_provider_disconnected, provider)
    live.pop(provider, None)
    request.app.state.channels_config = live
    return _provider_response(provider, live)
