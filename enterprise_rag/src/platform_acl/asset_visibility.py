"""Asset-level sharing ACL (private / tenant_shared / platform).

Complements document-level department ACL in ``security.access_control``
(public/internal/confidential). Use this for KB spaces, exam collections, etc.
"""

from __future__ import annotations

from typing import Any

VIS_PRIVATE = "private"
VIS_TENANT_SHARED = "tenant_shared"
VIS_PLATFORM = "platform"

ASSET_VISIBILITIES = (VIS_PRIVATE, VIS_TENANT_SHARED, VIS_PLATFORM)

DEFAULT_TENANT = "internal"


def normalize_asset_visibility(raw: str | None) -> str:
    s = (raw or "").strip().lower()
    if s in ("shared", "tenant", "org", "organization"):
        return VIS_TENANT_SHARED
    if s in ("public", "global", "catalog"):
        return VIS_PLATFORM
    if s in ASSET_VISIBILITIES:
        return s
    # Safe default for new personal content
    return VIS_PRIVATE


def can_read_asset(
    *,
    visibility: str | None,
    tenant_id: str | None,
    owner_user_id: str | None,
    reader_tenant_id: str | None,
    reader_user_id: str | None,
    reader_is_platform_admin: bool = False,
) -> bool:
    """Whether reader may use this asset (KB space / exam collection / …)."""
    vis = normalize_asset_visibility(visibility)
    asset_tenant = (tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    reader_tenant = (reader_tenant_id or DEFAULT_TENANT).strip() or DEFAULT_TENANT
    owner = (owner_user_id or "").strip()
    reader = (reader_user_id or "").strip()

    if vis == VIS_PLATFORM:
        return True
    if vis == VIS_TENANT_SHARED:
        return asset_tenant == reader_tenant
    # private
    if not reader:
        return False
    return bool(owner) and owner == reader


def filter_readable_assets(
    rows: list[dict[str, Any]],
    *,
    reader_tenant_id: str | None,
    reader_user_id: str | None,
    reader_is_platform_admin: bool = False,
) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if can_read_asset(
            visibility=str(row.get("visibility") or ""),
            tenant_id=str(row.get("tenant_id") or ""),
            owner_user_id=str(row.get("owner_user_id") or ""),
            reader_tenant_id=reader_tenant_id,
            reader_user_id=reader_user_id,
            reader_is_platform_admin=reader_is_platform_admin,
        ):
            out.append(row)
    return out
