"""TDD: weather tool must reject mismatched nearest_area (e.g. 萧山 → Sasayama)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "enterprise_rag" / "src"))

from agent.tools.builtins.weather import (  # noqa: E402
    get_weather,
    normalize_city_query,
    place_matches_request,
)

_FIXED_NOW = datetime(2026, 8, 7, 19, 15, tzinfo=ZoneInfo("Asia/Shanghai"))


@pytest.fixture(autouse=True)
def _fixed_beijing_now(monkeypatch):
    monkeypatch.setattr("agent.tools.builtins.weather.beijing_now", lambda: _FIXED_NOW)
    monkeypatch.setattr("agent.tools.builtins.datetime_cn.beijing_now", lambda: _FIXED_NOW)


def _fake_urlopen_payload(payload: dict):
    def _fake_urlopen(req, timeout=0):
        resp = MagicMock()
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    return _fake_urlopen


def test_place_matches_request_accepts_xiaoshan_variants():
    assert place_matches_request("萧山", "Xiaoshan", "China", "Zhejiang")
    assert place_matches_request("萧山", "杭州萧山区", "中国", "浙江")
    assert place_matches_request("杭州萧山", "Xiaoshan", "China", "Zhejiang")


def test_place_matches_request_rejects_japan_sasayama():
    assert not place_matches_request("萧山", "Sasayama", "Japan", "Hyogo")
    assert not place_matches_request("萧山", "篠山", "日本", "")


def test_normalize_city_query_prefers_hangzhou_xiaoshan():
    display, query = normalize_city_query("萧山")
    assert display == "萧山"
    assert "Xiaoshan" in query or "xiaoshan" in query.lower()
    assert "Hangzhou" in query or "hangzhou" in query.lower() or "杭州" in query


def test_weather_rejects_mismatched_nearest_area_and_exposes_guard():
    fake = {
        "current_condition": [
            {
                "temp_C": "28",
                "FeelsLikeC": "30",
                "humidity": "70",
                "windspeedKmph": "8",
                "lang_zh": [{"value": "晴"}],
                "observation_time": "10:00 AM",
            }
        ],
        "nearest_area": [
            {
                "areaName": [{"value": "Sasayama"}],
                "country": [{"value": "Japan"}],
                "region": [{"value": "Hyogo"}],
            }
        ],
        "weather": [],
    }

    with patch("urllib.request.urlopen", _fake_urlopen_payload(fake)):
        out = get_weather("萧山")

    assert "定位校验失败" in out
    assert "Sasayama" in out or "Japan" in out or "日本" in out
    assert "当前天气" not in out
    assert "28" not in out  # 禁止泄露错配地点气温


def test_weather_accepts_matched_xiaoshan_area():
    fake = {
        "current_condition": [
            {
                "temp_C": "33",
                "FeelsLikeC": "40",
                "humidity": "59",
                "windspeedKmph": "15",
                "lang_zh": [{"value": "局部多云"}],
                "observation_time": "11:15 AM",
            }
        ],
        "nearest_area": [
            {
                "areaName": [{"value": "Xiaoshan"}],
                "country": [{"value": "China"}],
                "region": [{"value": "Zhejiang"}],
            }
        ],
        "weather": [],
    }

    captured: list[str] = []

    def _capture_urlopen(req, timeout=0):
        captured.append(str(getattr(req, "full_url", None) or req))
        resp = MagicMock()
        resp.read.return_value = json.dumps(fake).encode("utf-8")
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", _capture_urlopen):
        out = get_weather("萧山")

    assert "定位校验失败" not in out
    assert "当前天气" in out
    assert "33" in out
    assert captured and ("Xiaoshan" in captured[0] or "xiaoshan" in captured[0].lower())
