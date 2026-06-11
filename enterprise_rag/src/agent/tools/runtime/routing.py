"""实时类问题识别：强制走 general + 对话工具。"""

from __future__ import annotations

import re

_REALTIME_RE = re.compile(
    r"今天|今日|现在|当前|此刻|几点|几月|几号|日期|星期|礼拜|周几|"
    r"北京时间|什么时间|什么时候|哪年|哪一年|哪一月|哪个月|哪天|"
    r"实时|最新|新闻|放假|节假日|调休|天气怎么样|天气如何",
    re.IGNORECASE,
)


def question_needs_agent_tools(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    return bool(_REALTIME_RE.search(q))
