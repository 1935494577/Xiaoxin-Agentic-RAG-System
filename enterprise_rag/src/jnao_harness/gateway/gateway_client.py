"""Proxy selected Harness Gateway APIs from the main RAG API (8010)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_GATEWAY_URL_ENV_KEYS = ("JNAO_HARNESS_GATEWAY_URL", "DEER_FLOW_CHANNELS_GATEWAY_URL")


def harness_gateway_url() -> str | None:
    for key in _GATEWAY_URL_ENV_KEYS:
        value = os.environ.get(key, "").strip().rstrip("/")
        if value:
            return value
    return None


async def proxy_gateway_json(
    method: str,
    path: str,
    *,
    timeout: float = 10.0,
    json: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    base = harness_gateway_url()
    if not base:
        return None
    url = f"{base}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, json=json)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        logger.debug("Harness gateway request failed: %s %s", method, url, exc_info=True)
        return None
    return payload if isinstance(payload, dict) else None
