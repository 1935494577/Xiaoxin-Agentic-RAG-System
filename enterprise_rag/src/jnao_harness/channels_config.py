"""Jnao channel connections settings (DeerFlow channel_connections subset)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.channels.registry import CHANNEL_REGISTRY
from config import settings

_DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "providers": {name: {"enabled": True} for name in CHANNEL_REGISTRY},
}


def _settings_path() -> Path:
    path = settings.data_processed_dir.parent / "channels" / "connections.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_channel_connections_settings() -> dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        return dict(_DEFAULT_SETTINGS)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return dict(_DEFAULT_SETTINGS)
    enabled = bool(raw.get("enabled", True))
    providers = raw.get("providers")
    if not isinstance(providers, dict):
        providers = _DEFAULT_SETTINGS["providers"]
    merged_providers: dict[str, dict[str, Any]] = {}
    for name in CHANNEL_REGISTRY:
        entry = providers.get(name) if isinstance(providers.get(name), dict) else {}
        merged_providers[name] = {"enabled": bool(entry.get("enabled", True))}
    return {"enabled": enabled, "providers": merged_providers}


def is_connections_enabled() -> bool:
    return bool(load_channel_connections_settings().get("enabled", True))


def is_provider_enabled(provider: str) -> bool:
    cfg = load_channel_connections_settings()
    if not cfg.get("enabled", True):
        return False
    providers = cfg.get("providers") or {}
    entry = providers.get(provider)
    if not isinstance(entry, dict):
        return False
    return bool(entry.get("enabled", False))


class _ProviderCfg:
    def __init__(self, enabled: bool):
        self.enabled = enabled


class _ConnectionsConfigShim:
    """Minimal stand-in for deerflow ChannelConnectionsConfig."""

    def __init__(self) -> None:
        cfg = load_channel_connections_settings()
        self.enabled = bool(cfg.get("enabled", True))
        for name in CHANNEL_REGISTRY:
            entry = cfg.get("providers", {}).get(name, {})
            enabled = bool(entry.get("enabled", True)) if isinstance(entry, dict) else True
            setattr(self, name, _ProviderCfg(enabled))

    def provider_status(self, provider: str) -> dict[str, bool]:
        enabled = is_provider_enabled(provider)
        return {"enabled": enabled, "configured": enabled}


def connections_config_shim() -> _ConnectionsConfigShim:
    return _ConnectionsConfigShim()


def merge_channels_config(base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge runtime UI credentials into channels config dict."""
    from app.channels.runtime_config_store import merge_runtime_channel_configs

    channels_config = dict(base or {})
    merge_runtime_channel_configs(channels_config, connections_config_shim())
    return channels_config
