"""天气查询工具（wttr.in：实况 + 数小时预报 + 出行建议）。"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any

from agent.tools.builtins.datetime_cn import beijing_now, format_beijing_time_anchor

DEFAULT_FORECAST_HOURS = 12
MAX_FORECAST_HOURS = 24

# 常用地名 → wttr 查询串（降低模糊匹配到国外同名/近音地点的概率）
_CITY_QUERY_ALIASES: dict[str, str] = {
    "萧山": "Xiaoshan,Hangzhou",
    "杭州萧山": "Xiaoshan,Hangzhou",
    "萧山区": "Xiaoshan,Hangzhou",
    "杭州": "Hangzhou",
    "北京": "Beijing",
    "上海": "Shanghai",
    "深圳": "Shenzhen",
    "广州": "Guangzhou",
    "成都": "Chengdu",
    "南京": "Nanjing",
    "武汉": "Wuhan",
    "西安": "Xian",
    "苏州": "Suzhou,China",
    "宁波": "Ningbo",
    "温州": "Wenzhou",
    "台州": "Taizhou,Zhejiang",
}

# 请求地名可用的匹配词（含中英别名）
_CITY_MATCH_ALIASES: dict[str, tuple[str, ...]] = {
    "萧山": ("萧山", "xiaoshan", "hangzhou"),
    "杭州萧山": ("萧山", "xiaoshan", "hangzhou"),
    "萧山区": ("萧山", "xiaoshan", "hangzhou"),
    "杭州": ("杭州", "hangzhou"),
    "北京": ("北京", "beijing"),
    "上海": ("上海", "shanghai"),
    "深圳": ("深圳", "shenzhen"),
    "广州": ("广州", "guangzhou"),
    "成都": ("成都", "chengdu"),
    "南京": ("南京", "nanjing"),
    "武汉": ("武汉", "wuhan"),
    "西安": ("西安", "xian", "xi'an"),
    "苏州": ("苏州", "suzhou"),
    "宁波": ("宁波", "ningbo"),
    "温州": ("温州", "wenzhou"),
    "台州": ("台州", "taizhou"),
}

_CHINA_MARKERS = ("china", "中国", "cn", "prc")
_FOREIGN_BLOCK = (
    "japan",
    "日本",
    "usa",
    "united states",
    "america",
    "韩国",
    "korea",
    "vietnam",
    "越南",
    "thailand",
    "泰国",
    "india",
    "印度",
)


def normalize_city_query(city: str) -> tuple[str, str]:
    """返回 (展示名, wttr 查询串)。"""
    name = (city or "").strip()
    if not name:
        return "", ""
    query = _CITY_QUERY_ALIASES.get(name) or name
    return name, query


def place_matches_request(
    requested: str,
    place: str,
    country: str = "",
    region: str = "",
) -> bool:
    """校验 wttr nearest_area 是否与用户请求城市一致。"""
    req = (requested or "").strip()
    if not req:
        return False
    place_l = (place or "").strip().lower()
    country_l = (country or "").strip().lower()
    region_l = (region or "").strip().lower()
    hay = " ".join(x for x in (place_l, region_l, country_l) if x)

    if country_l and any(m in country_l for m in _FOREIGN_BLOCK):
        # 中文城市名落到外国 → 一律拒绝
        if re.search(r"[\u4e00-\u9fff]", req):
            return False

    aliases = list(_CITY_MATCH_ALIASES.get(req, ()))
    aliases.append(req.lower())
    # 去掉「区/市/县」再匹配
    stripped = re.sub(r"[市区县]$", "", req)
    if stripped and stripped != req:
        aliases.append(stripped.lower())
        aliases.extend(_CITY_MATCH_ALIASES.get(stripped, ()))

    for alias in aliases:
        a = (alias or "").strip().lower()
        if not a:
            continue
        if a in hay or a in place_l:
            # 中国城市优先：若国家字段存在且明显非中国，仍拒绝
            if country_l and any(m in country_l for m in _FOREIGN_BLOCK):
                return False
            if country_l and not any(m in country_l for m in _CHINA_MARKERS):
                if re.search(r"[\u4e00-\u9fff]", req):
                    return False
            return True

    # 无别名时：双向包含（杭州萧山区 ⊇ 萧山）
    req_l = req.lower()
    if req_l in place_l or place_l in req_l:
        if country_l and any(m in country_l for m in _FOREIGN_BLOCK):
            return False
        return True
    return False


def _area_field(nearest: dict[str, Any], key: str) -> str:
    rows = nearest.get(key) or [{}]
    if isinstance(rows, list) and rows:
        first = rows[0]
        if isinstance(first, dict):
            return str(first.get("value") or "").strip()
        return str(first).strip()
    return ""


def get_weather(city: str, forecast_hours: int | None = None) -> str:
    name = (city or "").strip()
    if not name:
        return "请提供城市名称，例如：杭州、北京。"
    if len(name) > 64:
        return "城市名称过长。"

    hours = _clamp_hours(forecast_hours)
    display, query = normalize_city_query(name)

    url = f"https://wttr.in/{urllib.parse.quote(query)}?format=j1&lang=zh"
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
        return _fallback_plain(query)

    return _format_weather(data, display, hours)


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
    nearest = (data.get("nearest_area") or [{}])[0]
    if not isinstance(nearest, dict):
        nearest = {}
    place = _area_field(nearest, "areaName") or fallback_city
    country = _area_field(nearest, "country")
    region = _area_field(nearest, "region")

    if not place_matches_request(fallback_city, place, country, region):
        where = place
        if region:
            where = f"{where}/{region}"
        if country:
            where = f"{where}/{country}"
        return (
            f"【定位校验失败】天气服务将「{fallback_city}」解析为「{where}」，"
            f"与请求地点不符。请改用更完整地名（例如「杭州萧山」）后重试；"
            f"禁止使用该结果回答用户询问的城市天气。"
        )

    temp = cur.get("temp_C", "?")
    feel = cur.get("FeelsLikeC", "?")
    desc = _desc(cur)
    humidity = cur.get("humidity", "?")
    wind = cur.get("windspeedKmph", "?")
    obs = str(cur.get("observation_time") or "").strip()
    now = beijing_now()

    lines = [
        format_beijing_time_anchor(),
        (
            f"{place} 当前天气（北京时间 {now.strftime('%H:%M')}，"
            f"数据源观测 {obs or '刚刚'}）：{desc}，"
            f"气温 {temp}°C（体感 {feel}°C），湿度 {humidity}%，风速 {wind} km/h。"
        ),
        "",
    ]

    upcoming = _upcoming_hourly(data.get("weather") or [], now, forecast_hours)
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


def _time_label(time_code: str) -> str:
    n = int(time_code)
    if n == 0:
        return "00:00"
    return f"{n // 100:02d}:{n % 100:02d}"


def _slot_datetime(date_str: str, time_code: str) -> datetime | None:
    date_str = (date_str or "").strip()
    if not date_str:
        return None
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    n = int(time_code)
    hour, minute = (0, 0) if n == 0 else (n // 100, n % 100)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=beijing_now().tzinfo)


def _upcoming_hourly(
    weather_days: list[Any],
    now: datetime,
    forecast_hours: int,
) -> list[dict[str, Any]]:
    horizon_end = now + timedelta(hours=forecast_hours)
    out: list[dict[str, Any]] = []

    for day in weather_days:
        if not isinstance(day, dict):
            continue
        date_str = str(day.get("date") or "")
        hourly = day.get("hourly") or []
        for h in hourly:
            if not isinstance(h, dict):
                continue
            slot_dt = _slot_datetime(date_str, str(h.get("time", "0")))
            if slot_dt is None:
                continue
            if slot_dt <= now or slot_dt > horizon_end:
                continue
            label = f"{date_str} {_time_label(str(h.get('time', '0')))}".strip()
            row = dict(h)
            row["label"] = label
            row["_sort"] = slot_dt.timestamp()
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
