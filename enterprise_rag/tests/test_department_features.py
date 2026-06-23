"""Department feature mapping for API middleware."""

from __future__ import annotations

from security.department_features import can_access_feature, feature_for_request


def test_feature_for_scenario_catalog():
    assert feature_for_request("GET", "/config/scenario-catalog") == "scenarios"
    assert can_access_feature("运营部", "scenarios") is True
    assert can_access_feature("运营部", "eval_reports") is False


def test_feature_for_kb_health_blocked_for_ops():
    assert feature_for_request("POST", "/admin/eval/kb-health") == "eval_reports"
    assert can_access_feature("运营部", "eval_reports") is False
    assert can_access_feature("技术部", "eval_reports") is True


def test_feature_for_auth_admin_users():
    assert feature_for_request("GET", "/auth/admin/users") == "users"
    assert can_access_feature("运营部", "users") is False
    assert can_access_feature("技术部", "users") is True


def test_eval_reports_under_feedback():
    assert feature_for_request("GET", "/admin/feedback/eval-reports") == "eval_reports"
    assert feature_for_request("GET", "/admin/feedback") == "feedback"
