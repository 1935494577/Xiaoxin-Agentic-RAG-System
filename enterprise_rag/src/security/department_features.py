"""Department-based admin feature access for internal employees."""

from __future__ import annotations

from urllib.parse import unquote

FULL_ACCESS_DEPARTMENT = "技术部"

STANDARD_DEPARTMENT_FEATURES = frozenset({"ingest", "prompts", "models", "scenarios", "tutorial"})

KNOWN_DEPARTMENTS = frozenset({"技术部", "运营部", "媒体部", "剪辑部"})


def normalize_department(department: str | None) -> str:
    raw = (department or "").strip()
    if not raw:
        return ""
    return unquote(raw, encoding="utf-8", errors="replace").strip()


def should_enforce_department(department: str | None) -> bool:
    dept = normalize_department(department)
    return bool(dept) and dept in KNOWN_DEPARTMENTS


def has_full_department_access(department: str | None) -> bool:
    return normalize_department(department) == FULL_ACCESS_DEPARTMENT


def can_access_feature(department: str | None, feature: str) -> bool:
    if not should_enforce_department(department):
        return True
    if has_full_department_access(department):
        return True
    return feature in STANDARD_DEPARTMENT_FEATURES


def feature_for_request(method: str, path: str) -> str | None:
    """Map API path (+ method) to an admin feature id, or None if unrestricted."""
    m = (method or "GET").upper()
    p = path.split("?", 1)[0].rstrip("/") or "/"
    if p.startswith("/api/v1"):
        p = p[len("/api/v1") :] or "/"

    if p == "/health" or p == "/config/nav" or p == "/config/public":
        return None

    if p.startswith("/config/scenario-catalog"):
        return "scenarios"

    if p.startswith("/ingest/"):
        return "ingest"

    if p.startswith("/config/prompts"):
        return "prompts"

    if p.startswith("/config/model-profiles"):
        return "models"

    if p.startswith("/config/processing-tools") or p.startswith("/config/agent-tools"):
        return "processing"

    if p.startswith("/config/vector-stores"):
        return "vector_store"

    if p.startswith("/config/ui"):
        if m == "GET":
            return None
        return "memory"

    if p.startswith("/admin/feedback/eval-reports") or p.startswith("/admin/eval/"):
        return "eval_reports"

    if p.startswith("/admin/feedback"):
        return "feedback"

    if p.startswith("/auth/admin"):
        return "users"

    if p.startswith("/debug/trace-status"):
        return "trace"

    return None
