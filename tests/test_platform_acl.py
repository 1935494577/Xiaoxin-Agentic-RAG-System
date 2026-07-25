"""TDD: asset visibility ACL."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "enterprise_rag" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_private_only_owner():
    from platform_acl import can_read_asset

    assert can_read_asset(
        visibility="private",
        tenant_id="internal",
        owner_user_id="u1",
        reader_tenant_id="internal",
        reader_user_id="u1",
    )
    assert not can_read_asset(
        visibility="private",
        tenant_id="internal",
        owner_user_id="u1",
        reader_tenant_id="internal",
        reader_user_id="u2",
    )


def test_tenant_shared_same_tenant():
    from platform_acl import can_read_asset

    assert can_read_asset(
        visibility="tenant_shared",
        tenant_id="school-a",
        owner_user_id="u1",
        reader_tenant_id="school-a",
        reader_user_id="u2",
    )
    assert not can_read_asset(
        visibility="tenant_shared",
        tenant_id="school-a",
        owner_user_id="u1",
        reader_tenant_id="school-b",
        reader_user_id="u2",
    )


def test_platform_readable():
    from platform_acl import can_read_asset, normalize_asset_visibility

    assert normalize_asset_visibility("shared") == "tenant_shared"
    assert can_read_asset(
        visibility="platform",
        tenant_id="platform",
        owner_user_id="ops",
        reader_tenant_id="school-a",
        reader_user_id="u9",
    )


def test_batch_ingest_empty_owner_needs_tenant_shared():
    """Batch ingest creates collections without owner; private hides them from logged-in users."""
    from platform_acl import can_read_asset

    assert not can_read_asset(
        visibility="private",
        tenant_id="internal",
        owner_user_id="",
        reader_tenant_id="internal",
        reader_user_id="tech1",
    )
    assert can_read_asset(
        visibility="tenant_shared",
        tenant_id="internal",
        owner_user_id="",
        reader_tenant_id="internal",
        reader_user_id="tech1",
    )
