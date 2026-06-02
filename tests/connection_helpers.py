"""前后端连通性检测（pytest / 运维脚本；实现见 api.connectivity）。"""

from api.connectivity import (
    DEFAULT_API,
    DOCUMENTED_API_PORT,
    FRONTEND_PORT,
    HEALTH_TIMEOUT,
    PUBLIC_CONFIG_KEYS,
    RETRY_COUNT,
    RETRY_INTERVAL_SEC,
    auth_headers_from_env as api_auth_headers,
    check_api_with_retry,
    fetch_public_config,
    ping_api_ready,
    ping_health,
    verify_frontend_backend_sync,
)

__all__ = [
    "DEFAULT_API",
    "DOCUMENTED_API_PORT",
    "FRONTEND_PORT",
    "HEALTH_TIMEOUT",
    "PUBLIC_CONFIG_KEYS",
    "RETRY_COUNT",
    "RETRY_INTERVAL_SEC",
    "api_auth_headers",
    "check_api_with_retry",
    "fetch_public_config",
    "ping_api_ready",
    "ping_health",
    "verify_frontend_backend_sync",
]
