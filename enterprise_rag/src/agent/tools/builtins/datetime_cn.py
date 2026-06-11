"""当前北京时间（无需联网）。"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
_TZ = ZoneInfo("Asia/Shanghai")


def get_beijing_time() -> str:
    now = datetime.now(_TZ)
    weekday = _WEEKDAYS[now.weekday()]
    return (
        f"北京时间：{now.strftime('%Y年%m月%d日')} {weekday} "
        f"{now.strftime('%H:%M:%S')}（时区 Asia/Shanghai，UTC+8）"
    )
