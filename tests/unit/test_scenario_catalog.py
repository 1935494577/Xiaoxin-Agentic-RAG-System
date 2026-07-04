"""Scenario catalog API — department features + dev tech map."""

from __future__ import annotations

from api.scenario_catalog import list_scenarios_for_department, public_scenario_catalog
from security.department_features import FULL_ACCESS_DEPARTMENT


def test_public_catalog_for_ops_department():
    data = public_scenario_catalog("运营部", include_tech=False)
    assert data["department"] == "运营部"
    assert data["show_tech"] is False
    ids = {s["id"] for s in data["scenarios"]}
    assert "wecom_parent_dm" in ids
    assert "short_video_script" not in ids
    assert all("tech" not in s for s in data["scenarios"])


def test_tech_included_for_tech_department():
    data = public_scenario_catalog(FULL_ACCESS_DEPARTMENT)
    assert data["show_tech"] is True
    row = next(s for s in data["scenarios"] if s["id"] == "wecom_parent_dm")
    assert "tech" in row
    assert row["tech"].get("stream_api") == "POST /chat/stream"


def test_list_scenarios_media_department():
    rows = list_scenarios_for_department("媒体部")
    ids = {r["id"] for r in rows}
    assert "short_video_script" in ids
    assert "wecom_parent_dm" not in ids
