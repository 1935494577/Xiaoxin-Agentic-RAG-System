"""当前北京时间（无需联网）。"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
_TZ = ZoneInfo("Asia/Shanghai")


def beijing_now() -> datetime:
    return datetime.now(_TZ)


def day_period(hour: int) -> str:
    if hour < 6:
        return "凌晨"
    if hour < 12:
        return "上午"
    if hour < 18:
        return "下午"
    return "晚上"


def format_beijing_time_anchor() -> str:
    """Server-side anchor for realtime tool answers — LLM must align user-facing time to this."""
    now = beijing_now()
    weekday = _WEEKDAYS[now.weekday()]
    period = day_period(now.hour)
    return (
        f"【时间基准】北京时间：{now.strftime('%Y年%m月%d日')} {weekday} "
        f"{period} {now.strftime('%H:%M')}（向用户汇报日期与时刻必须与此一致；"
        f"预报/日程仅描述该时刻之后的时段）"
    )


def get_beijing_time() -> str:
    now = beijing_now()
    weekday = _WEEKDAYS[now.weekday()]
    period = day_period(now.hour)
    return (
        f"{format_beijing_time_anchor()}\n"
        f"北京时间：{now.strftime('%Y年%m月%d日')} {weekday} {period} "
        f"{now.strftime('%H:%M:%S')}（时区 Asia/Shanghai，UTC+8）"
    )
