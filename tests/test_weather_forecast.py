"""Tests for weather forecast and advice."""

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

from agent.tools.builtins.weather import get_weather  # noqa: E402

_FIXED_NOW = datetime(2026, 6, 11, 10, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


@pytest.fixture(autouse=True)
def _fixed_beijing_now(monkeypatch):
    monkeypatch.setattr("agent.tools.builtins.weather.beijing_now", lambda: _FIXED_NOW)
    monkeypatch.setattr("agent.tools.builtins.datetime_cn.beijing_now", lambda: _FIXED_NOW)


def _hourly(time: str, temp: str, desc: str, rain: str = "0") -> dict:
    return {
        "time": time,
        "tempC": temp,
        "lang_zh": [{"value": desc}],
        "chanceofrain": rain,
        "windspeedKmph": "12",
    }


def test_weather_includes_hourly_forecast_and_advice():
    fake = {
        "current_condition": [
            {
                "temp_C": "22",
                "FeelsLikeC": "21",
                "humidity": "60",
                "windspeedKmph": "10",
                "lang_zh": [{"value": "晴"}],
                "observation_time": "10:00 AM",
            }
        ],
        "nearest_area": [{"areaName": [{"value": "杭州"}]}],
        "weather": [
            {
                "date": "2026-06-11",
                "hourly": [
                    _hourly("900", "20", "多云"),
                    _hourly("1200", "24", "晴"),
                    _hourly("1500", "26", "晴"),
                    _hourly("1800", "23", "小雨", "70"),
                ],
            }
        ],
    }

    def _fake_urlopen(req, timeout=0):
        resp = MagicMock()
        resp.read.return_value = json.dumps(fake).encode("utf-8")
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", _fake_urlopen):
        out = get_weather("杭州", forecast_hours=12)

    assert "【时间基准】" in out
    assert "10:30" in out
    assert "当前天气" in out
    assert "未来" in out
    assert "12:00" in out
    assert "18:00" in out
    assert "建议" in out
    assert "雨" in out


def test_weather_respects_forecast_hours_param():
    fake = {
        "current_condition": [
            {
                "temp_C": "15",
                "FeelsLikeC": "14",
                "humidity": "50",
                "windspeedKmph": "5",
                "lang_zh": [{"value": "阴"}],
                "observation_time": "08:00 AM",
            }
        ],
        "nearest_area": [{"areaName": [{"value": "北京"}]}],
        "weather": [{"date": "2026-06-11", "hourly": [_hourly("900", "18", "阴"), _hourly("1200", "22", "晴")]}],
    }

    def _fake_urlopen(req, timeout=0):
        resp = MagicMock()
        resp.read.return_value = json.dumps(fake).encode("utf-8")
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", _fake_urlopen):
        out = get_weather("北京", forecast_hours=3)

    assert "09:00" not in out
    assert "12:00" in out


def test_weather_excludes_past_hours_against_beijing_now(monkeypatch):
    evening = datetime(2026, 6, 16, 19, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    monkeypatch.setattr("agent.tools.builtins.weather.beijing_now", lambda: evening)
    monkeypatch.setattr("agent.tools.builtins.datetime_cn.beijing_now", lambda: evening)

    fake = {
        "current_condition": [
            {
                "temp_C": "25",
                "FeelsLikeC": "27",
                "humidity": "83",
                "windspeedKmph": "5",
                "lang_zh": [{"value": "部分多云"}],
                "observation_time": "02:33 AM",
            }
        ],
        "nearest_area": [{"areaName": [{"value": "杭州萧山区"}]}],
        "weather": [
            {
                "date": "2026-06-16",
                "hourly": [
                    _hourly("300", "22", "薄雾", "44"),
                    _hourly("600", "22", "薄雾", "50"),
                    _hourly("900", "24", "零星小雨", "27"),
                    _hourly("1200", "29", "附近有阵雨", "17"),
                    _hourly("2100", "23", "多云", "10"),
                ],
            },
            {
                "date": "2026-06-17",
                "hourly": [_hourly("300", "22", "薄雾", "40")],
            },
        ],
    }

    def _fake_urlopen(req, timeout=0):
        resp = MagicMock()
        resp.read.return_value = json.dumps(fake).encode("utf-8")
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", _fake_urlopen):
        out = get_weather("杭州萧山", forecast_hours=12)

    assert "2026年06月16日" in out
    assert "19:30" in out
    assert "2026-06-16 03:00" not in out
    assert "2026-06-16 06:00" not in out
    assert "2026-06-16 12:00" not in out
    assert "21:00" in out
    assert "2026-06-17 03:00" in out
