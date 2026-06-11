"""ACL: department + visibility for retrieval."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from security.access_control import (  # noqa: E402
    can_access_document,
    can_access_row,
    normalize_department,
    normalize_visibility,
)


def test_normalize_department_aliases():
    assert normalize_department("技术") == "技术部"
    assert normalize_department("general") == "技术部"
    assert normalize_department("运营") == "运营部"


def test_public_visible_to_all_departments():
    assert can_access_document("技术部", "public", "运营部")
    assert can_access_document("媒体部", "public", "剪辑部")


def test_internal_only_same_department():
    assert can_access_document("技术部", "internal", "技术部")
    assert not can_access_document("技术部", "internal", "运营部")


def test_confidential_blocked():
    assert not can_access_document("技术部", "confidential", "技术部")


def test_missing_visibility_treated_as_internal():
    assert can_access_document("技术部", None, "技术部")
    assert not can_access_document("技术部", None, "媒体部")


def test_can_access_row_uses_metadata():
    row = {"department": "运营部", "permission_label": "public"}
    assert can_access_row(row, "技术部")
    row_internal = {"department": "运营部", "permission_label": "internal"}
    assert not can_access_row(row_internal, "技术部")
    assert can_access_row(row_internal, "运营部")
