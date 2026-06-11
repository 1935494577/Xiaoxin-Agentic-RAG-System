"""Document visibility ACL: department + internal/public scope."""

from __future__ import annotations

from config import settings

VISIBILITY_PUBLIC = "public"
VISIBILITY_INTERNAL = "internal"
VISIBILITY_CONFIDENTIAL = "confidential"

DEPARTMENTS: tuple[str, ...] = ("技术部", "运营部", "媒体部", "剪辑部")

_LEGACY_DEPARTMENT_ALIASES: dict[str, str] = {
    "general": "技术部",
    "技术": "技术部",
    "运营": "运营部",
    "市场": "运营部",
    "媒体": "媒体部",
    "剪辑": "剪辑部",
    "人事": "运营部",
    "财务": "运营部",
    "hr": "运营部",
}


def normalize_department(name: str | None) -> str:
    s = (name or "").strip()
    if not s:
        return normalize_department(settings.default_department)
    if s in _LEGACY_DEPARTMENT_ALIASES:
        return _LEGACY_DEPARTMENT_ALIASES[s]
    return s


def normalize_visibility(label: str | None) -> str:
    s = (label or "").strip().lower()
    if s in (VISIBILITY_PUBLIC, VISIBILITY_INTERNAL, VISIBILITY_CONFIDENTIAL):
        return s
    # Legacy rows without visibility: treat as internal (same as old dept-only filter).
    if not s:
        return VISIBILITY_INTERNAL
    return VISIBILITY_PUBLIC


def can_access_document(
    doc_department: str | None,
    doc_visibility: str | None,
    user_department: str | None,
) -> bool:
    vis = normalize_visibility(doc_visibility)
    if vis == VISIBILITY_CONFIDENTIAL:
        return False
    if vis == VISIBILITY_PUBLIC:
        return True
    doc_dept = normalize_department(doc_department)
    user_dept = normalize_department(user_department)
    return doc_dept == user_dept


def can_access_row(row: dict, user_department: str | None) -> bool:
    return can_access_document(
        str(row.get("department") or ""),
        str(row.get("permission_label") or ""),
        user_department,
    )


def milvus_access_expr(user_department: str, *, has_permission_field: bool) -> str | None:
    if not user_department:
        return None
    dept = normalize_department(user_department).replace("\\", "\\\\").replace('"', '\\"')
    if not has_permission_field:
        return f'department == "{dept}"'
    return (
        f'(permission_label == "{VISIBILITY_PUBLIC}") or '
        f'(permission_label == "{VISIBILITY_INTERNAL}" and department == "{dept}")'
    )
