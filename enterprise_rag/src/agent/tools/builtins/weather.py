"""天气查询工具（wttr.in：实况 + 数小时预报 + 出行建议）。"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

DEFAULT_FORECAST_HOURS = 12
MAX_FORECAST_HOURS = 24


def get_weather(city: str, forecast_hours: int | None = None) -> str:
    name = (city or "").strip()
    if not name:
        return "请提供城市名称，例如：杭州、北京。"
    if len(name) > 64:
        return "城市名称过长。"

    hours = _clamp_hours(forecast_hours)

    url = f"https://wttr.in/{urllib.parse.quote(name)}?format=j1&lang=zh"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "enterprise-rag/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        return f"天气服务暂时不可用：{e.reason or e}"
    except TimeoutError:
        return "天气查询超时，请稍后重试。"

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_plain(name)

    return _format_weather(data, name, hours)


def _clamp_hours(forecast_hours: int | None) -> int:
    if forecast_hours is None:
        return DEFAULT_FORECAST_HOURS
    try:
        h = int(forecast_hours)
    except (TypeError, ValueError):
        return DEFAULT_FORECAST_HOURS
    return max(3, min(h, MAX_FORECAST_HOURS))


def _fallback_plain(name: str) -> str:
    plain_url = f"https://wttr.in/{urllib.parse.quote(name)}?format=3"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(plain_url, headers={"User-Agent": "enterprise-rag/1.0"}),
            timeout=6,
        ) as resp2:
            line = resp2.read().decode("utf-8", errors="replace").strip()
            return line or f"未找到「{name}」的天气信息。"
    except Exception:
        return f"未能解析「{name}」的天气数据。"


def _format_weather(data: dict[str, Any], fallback_city: str, forecast_hours: int) -> str:
    cur = (data.get("current_condition") or [{}])[0]
    area = ((data.get("nearest_area") or [{}])[0].get("areaName") or [{}])[0]
    place = str(area.get("value") or fallback_city)
    temp = cur.get("temp_C", "?")
    feel = cur.get("FeelsLikeC", "?")
    desc = _desc(cur)
    humidity = cur.get("humidity", "?")
    wind = cur.get("windspeedKmph", "?")
    obs = str(cur.get("observation_time") or "").strip()

    lines = [
        f"{place} 当前天气（观测 {obs or '刚刚'}）：{desc}，"
        f"气温 {temp}°C（体感 {feel}°C），湿度 {humidity}%，风速 {wind} km/h。",
        "",
    ]

    upcoming = _upcoming_hourly(data.get("weather") or [], obs, forecast_hours)
    if upcoming:
        lines.append(f"未来约 {forecast_hours} 小时预报（3 小时步长）：")
        for slot in upcoming:
            rain = slot.get("chanceofrain", "0")
            rain_note = f"，降水概率 {rain}%" if int(rain or 0) > 0 else ""
            lines.append(
                f"- {slot['label']}：{_desc(slot)}，{slot.get('tempC', '?')}°C{rain_note}"
            )
        lines.append("")

    advice = _build_advice(cur, upcoming)
    lines.append(f"【建议】{advice}")
    return "\n".join(lines).strip()


def _desc(row: dict[str, Any]) -> str:
    raw = row.get("lang_zh") or row.get("weatherDesc") or ""
    if isinstance(raw, list) and raw:
        raw = raw[0].get("value") if isinstance(raw[0], dict) else raw[0]
    text = re.sub(r"<[^>]+>", "", str(raw)).strip()
    return text or "未知"


def _slot_minutes(time_code: str) -> int:
    n = int(time_code)
    if n == 0:
        return 0
    return (n // 100) * 60 + (n % 100)


def _time_label(time_code: str) -> str:
    n = int(time_code)
    if n == 0:
        return "00:00"
    return f"{n // 100:02d}:{n % 100:02d}"


def _parse_observation_minutes(obs: str) -> int | None:
    obs = obs.strip()
    if not obs:
        return None
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            dt = datetime.strptime(obs, fmt)
            return dt.hour * 60 + dt.minute
        except ValueError:
            continue
    return None


def _upcoming_hourly(
    weather_days: list[Any],
    observation_time: str,
    forecast_hours: int,
) -> list[dict[str, Any]]:
    now_min = _parse_observation_minutes(observation_time)
    horizon = forecast_hours * 60
    out: list[dict[str, Any]] = []

    for day_idx, day in enumerate(weather_days):
        if not isinstance(day, dict):
            continue
        date_str = str(day.get("date") or "")
        hourly = day.get("hourly") or []
        for h in hourly:
            if not isinstance(h, dict):
                continue
            slot_min = _slot_minutes(str(h.get("time", "0")))
            if now_min is not None:
                day_offset = day_idx * 24 * 60
                delta = day_offset + slot_min - now_min
                if delta <= 0:
                    continue
                if delta > horizon:
                    continue
            label = f"{date_str} {_time_label(str(h.get('time', '0')))}".strip()
            row = dict(h)
            row["label"] = label
            row["_sort"] = day_idx * 24 * 60 + slot_min
            out.append(row)

    out.sort(key=lambda x: x.get("_sort", 0))
    for row in out:
        row.pop("_sort", None)
    return out


def _build_advice(current: dict[str, Any], upcoming: list[dict[str, Any]]) -> str:
    tips: list[str] = []

    try:
        temp = int(float(current.get("temp_C") or 0))
    except (TypeError, ValueError):
        temp = 20

    try:
        wind = int(float(current.get("windspeedKmph") or 0))
    except (TypeError, ValueError):
        wind = 0

    rain_chances = []
    temps = [temp]
    for h in upcoming:
        try:
            rain_chances.append(int(h.get("chanceofrain") or 0))
        except (TypeError, ValueError):
            pass
        try:
            temps.append(int(float(h.get("tempC") or 0)))
        except (TypeError, ValueError):
            pass

    max_rain = max(rain_chances) if rain_chances else 0
    min_t, max_t = min(temps), max(temps)

    if max_rain >= 60:
        tips.append("未来几小时降水概率较高，建议携带雨具，尽量避免长时间户外停留")
    elif max_rain >= 30:
        tips.append("可能有阵雨，外出建议备伞")
    elif max_rain >= 15:
        tips.append("偶有降雨可能，可按需备伞")

    if temp >= 33 or max_t >= 35:
        tips.append("气温偏高，注意防暑补水、防晒，避免正午暴晒")
    elif temp <= 5 or min_t <= 3:
        tips.append("气温较低，注意保暖，建议厚外套")
    elif temp <= 12 or min_t <= 10:
        tips.append("偏凉，建议外套或薄羽绒")

    if wind >= 40:
        tips.append("风力较大，减少高空或户外作业，注意出行安全")
    elif wind >= 25:
        tips.append("风较大，骑行或户外请注意防风")

    desc = _desc(current).lower()
    if max_rain < 20 and 15 <= temp <= 28 and wind < 25:
        if any(k in desc for k in ("晴", "clear", "sun")):
            tips.append("整体较舒适，适宜散步或短时户外活动")

    if not tips:
        tips.append("天气总体平稳，请根据体感适时增减衣物")

    return "；".join(tips)
