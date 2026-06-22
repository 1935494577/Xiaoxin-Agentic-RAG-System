"""Tests for query robustness offline eval."""

from __future__ import annotations

from evaluation.query_robustness_eval import run_query_robustness_eval


def test_query_robustness_eval_all_pass():
    report = run_query_robustness_eval()
    assert report["total"] >= 5
    assert report["failed"] == 0
    assert report["pass_rate"] == 1.0
    assert "by_scenario" in report
    assert report["by_scenario"]["training_kb"]["passed"] >= 2
