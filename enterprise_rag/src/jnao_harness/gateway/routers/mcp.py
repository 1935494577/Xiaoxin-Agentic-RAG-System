"""MCP server configuration API for Main API (8010) admin."""

from __future__ import annotations

import logging
import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from jnao_harness.gateway.auth import require_admin_user
from jnao_harness.gateway.gateway_client import proxy_gateway_json
from jnao_harness.mcp_config_store import (
    read_mcp_servers_raw,
    reset_local_mcp_cache_if_available,
    write_mcp_servers,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])

_ADMIN_REQUIRED_DETAIL = "Admin privileges required to manage MCP configuration."

_MCP_STDIO_COMMAND_ALLOWLIST_ENV = "DEER_FLOW_MCP_STDIO_COMMAND_ALLOWLIST"
_DEFAULT_MCP_STDIO_COMMAND_ALLOWLIST = frozenset({"npx", "uvx"})
_SHELL_METACHARS = frozenset(";|&`$<>\n\r")
_MASKED_VALUE = "***"


class McpOAuthConfigResponse(BaseModel):
    enabled: bool = Field(default=True)
    token_url: str = Field(default="")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(default="client_credentials")
    client_id: str | None = Field(default=None)
    client_secret: str | None = Field(default=None)
    refresh_token: str | None = Field(default=None)
    scope: str | None = Field(default=None)
    audience: str | None = Field(default=None)
    token_field: str = Field(default="access_token")
    token_type_field: str = Field(default="token_type")
    expires_in_field: str = Field(default="expires_in")
    default_token_type: str = Field(default="Bearer")
    refresh_skew_seconds: int = Field(default=60)
    extra_token_params: dict[str, str] = Field(default_factory=dict)


class McpServerConfigResponse(BaseModel):
    enabled: bool = Field(default=True)
    type: str = Field(default="stdio", description="stdio | sse | http")
    command: str | None = Field(default=None)
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = Field(default=None)
    headers: dict[str, str] = Field(default_factory=dict)
    oauth: McpOAuthConfigResponse | None = Field(default=None)
    description: str = Field(default="")


class McpConfigResponse(BaseModel):
    mcp_servers: dict[str, McpServerConfigResponse] = Field(default_factory=dict)


class McpConfigUpdateRequest(BaseModel):
    mcp_servers: dict[str, McpServerConfigResponse] = Field(...)


class McpCacheResetResponse(BaseModel):
    success: bool
    message: str


def _allowed_stdio_commands() -> set[str]:
    raw = os.environ.get(_MCP_STDIO_COMMAND_ALLOWLIST_ENV)
    base = set(_DEFAULT_MCP_STDIO_COMMAND_ALLOWLIST)
    if raw is None:
        return base
    extra = {item.strip() for item in raw.split(",") if item.strip()}
    return base | extra


def _stdio_command_name(command: str | None, *, server_name: str) -> str:
    if command is None or not command.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MCP server '{server_name}' with stdio transport requires a command.",
        )
    stripped = command.strip()
    has_path_separator = "/" in stripped or "\\" in stripped
    if stripped != command or has_path_separator or any(ch.isspace() for ch in stripped) or any(ch in stripped for ch in _SHELL_METACHARS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"MCP server '{server_name}' command must be a single executable name; "
                "put parameters in args instead."
            ),
        )
    return stripped


def _validate_mcp_update_request(request: McpConfigUpdateRequest) -> None:
    allowed_commands = _allowed_stdio_commands()
    for name, server in request.mcp_servers.items():
        transport_type = (server.type or "stdio").lower()
        if transport_type == "stdio":
            command_name = _stdio_command_name(server.command, server_name=name)
            if command_name not in allowed_commands:
                allowed = ", ".join(sorted(allowed_commands)) or "<none>"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"MCP server '{name}' uses disallowed stdio command '{command_name}'. "
                        f"Allowed commands: {allowed}. Configure {_MCP_STDIO_COMMAND_ALLOWLIST_ENV} to extend."
                    ),
                )
        elif transport_type in ("sse", "http"):
            if not (server.url or "").strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"MCP server '{name}' with {transport_type} transport requires a url.",
                )


def _mask_server_config(server: McpServerConfigResponse) -> McpServerConfigResponse:
    masked_env = {k: _MASKED_VALUE for k in server.env}
    masked_headers = {k: _MASKED_VALUE for k in server.headers}
    masked_oauth = None
    if server.oauth is not None:
        masked_oauth = server.oauth.model_copy(update={"client_secret": None, "refresh_token": None})
    return server.model_copy(
        update={"env": masked_env, "headers": masked_headers, "oauth": masked_oauth},
    )


def _merge_preserving_secrets(
    incoming: McpServerConfigResponse,
    existing: McpServerConfigResponse,
) -> McpServerConfigResponse:
    merged_env: dict[str, str] = {}
    for k, v in incoming.env.items():
        if v == _MASKED_VALUE:
            if k in existing.env:
                merged_env[k] = existing.env[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set env key '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_env[k] = v

    merged_headers: dict[str, str] = {}
    for k, v in incoming.headers.items():
        if v == _MASKED_VALUE:
            if k in existing.headers:
                merged_headers[k] = existing.headers[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set header '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_headers[k] = v

    merged_oauth = incoming.oauth
    if incoming.oauth is not None and existing.oauth is not None:
        merged_client_secret = (
            existing.oauth.client_secret
            if incoming.oauth.client_secret is None
            else (None if incoming.oauth.client_secret == "" else incoming.oauth.client_secret)
        )
        merged_refresh_token = (
            existing.oauth.refresh_token
            if incoming.oauth.refresh_token is None
            else (None if incoming.oauth.refresh_token == "" else incoming.oauth.refresh_token)
        )
        merged_oauth = incoming.oauth.model_copy(
            update={"client_secret": merged_client_secret, "refresh_token": merged_refresh_token},
        )
    return incoming.model_copy(update={"env": merged_env, "headers": merged_headers, "oauth": merged_oauth})


def _servers_from_raw(raw_servers: dict[str, dict]) -> dict[str, McpServerConfigResponse]:
    out: dict[str, McpServerConfigResponse] = {}
    for name, raw in raw_servers.items():
        try:
            out[name] = McpServerConfigResponse(**raw)
        except Exception:
            logger.warning("Skipping invalid MCP server config for %r", name, exc_info=True)
    return out


async def _reset_gateway_mcp_cache() -> None:
    await proxy_gateway_json("POST", "/api/mcp/cache/reset", timeout=15.0)


@router.get("/mcp/config", response_model=McpConfigResponse)
async def get_mcp_configuration(request: Request) -> McpConfigResponse:
    await require_admin_user(request, detail=_ADMIN_REQUIRED_DETAIL)
    servers = {
        name: _mask_server_config(server)
        for name, server in _servers_from_raw(read_mcp_servers_raw()).items()
    }
    return McpConfigResponse(mcp_servers=servers)


@router.post("/mcp/cache/reset", response_model=McpCacheResetResponse)
async def reset_mcp_tools_cache_endpoint(request: Request) -> McpCacheResetResponse:
    await require_admin_user(request, detail=_ADMIN_REQUIRED_DETAIL)
    reset_local_mcp_cache_if_available()
    await _reset_gateway_mcp_cache()
    return McpCacheResetResponse(
        success=True,
        message="MCP 工具缓存已重置，下次对话将重新加载 MCP 工具。",
    )


@router.put("/mcp/config", response_model=McpConfigResponse)
async def update_mcp_configuration(request: Request, body: McpConfigUpdateRequest) -> McpConfigResponse:
    try:
        await require_admin_user(request, detail=_ADMIN_REQUIRED_DETAIL)
        _validate_mcp_update_request(body)

        raw_servers = read_mcp_servers_raw()
        merged_servers: dict[str, McpServerConfigResponse] = {}
        for name, incoming in body.mcp_servers.items():
            raw_server = raw_servers.get(name)
            if raw_server is not None:
                merged_servers[name] = _merge_preserving_secrets(
                    incoming,
                    McpServerConfigResponse(**raw_server),
                )
            else:
                merged_servers[name] = incoming

        config_path = write_mcp_servers(
            {name: server.model_dump(exclude_none=False) for name, server in merged_servers.items()}
        )
        logger.info("MCP configuration updated: %s", config_path)
        reset_local_mcp_cache_if_available()
        await _reset_gateway_mcp_cache()

        servers = {name: _mask_server_config(server) for name, server in merged_servers.items()}
        return McpConfigResponse(mcp_servers=servers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update MCP configuration: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update MCP configuration: {e}") from e
