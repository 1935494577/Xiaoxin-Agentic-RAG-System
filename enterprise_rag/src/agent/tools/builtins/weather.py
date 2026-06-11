"""天气查询工具（wttr.in，无需 API Key）。"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request


def get_weather(city: str) -> str:
    name = (city or "").strip()
    if not name:
        return "请提供城市名称，例如：杭州、北京。"
    if len(name) > 64:
        return "城市名称过长。"

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

    cur = (data.get("current_condition") or [{}])[0]
    area = ((data.get("nearest_area") or [{}])[0].get("areaName") or [{}])[0]
    place = str(area.get("value") or name)
    temp = cur.get("temp_C", "?")
    feel = cur.get("FeelsLikeC", "?")
    desc = str(cur.get("lang_zh") or cur.get("weatherDesc") or "")
    if isinstance(desc, list) and desc:
        desc = str(desc[0].get("value") or "")
    desc = re.sub(r"<[^>]+>", "", desc).strip() or "未知"
    humidity = cur.get("humidity", "?")
    wind = cur.get("windspeedKmph", "?")
    return (
        f"{place} 当前天气：{desc}，气温 {temp}°C（体感 {feel}°C），"
        f"湿度 {humidity}%，风速 {wind} km/h。"
    )
