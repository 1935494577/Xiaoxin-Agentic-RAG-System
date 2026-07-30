"""Detect short greetings / courtesy so chat can skip retrieval."""

from __future__ import annotations

import re

_EXACT = frozenset(
    {
        "你好",
        "您好",
        "嗨",
        "哈喽",
        "早上好",
        "中午好",
        "下午好",
        "晚上好",
        "早",
        "晚安",
        "谢谢",
        "谢谢你",
        "谢谢您",
        "多谢",
        "感谢",
        "辛苦了",
        "再见",
        "拜拜",
        "回见",
        "在吗",
        "在不在",
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "bye",
        "ok",
        "好的",
        "嗯",
        "哦",
        "收到",
    }
)

# Whole-message short courtesy (no KB-looking content)
_PATTERNS = (
    re.compile(r"^(你好|您好|嗨|哈喽)[!！。.~～\s]*$"),
    re.compile(r"^(谢谢|多谢|感谢)(你|您|啦|了)?[!！。.~～\s]*$"),
    re.compile(r"^(再见|拜拜|回见)[!！。.~～\s]*$"),
    re.compile(r"^(早上好|中午好|下午好|晚上好|晚安)[!！。.~～\s]*$"),
    re.compile(r"^(hi|hello|hey|thanks|bye)[!!.\s]*$", re.I),
)


def _normalize(message: str) -> str:
    q = (message or "").strip()
    q = q.strip("！!。.？?~～… ")
    return q.strip().lower() if q.isascii() else q.strip()


def is_chitchat_message(message: str) -> bool:
    """True when the turn is pure greeting/courtesy and should skip KB retrieval."""
    raw = (message or "").strip()
    if not raw or len(raw) > 24:
        return False
    # Mixed greeting + real question → not chitchat
    if "，" in raw or "," in raw or "？" in raw or "?" in raw:
        # allow trailing ? on pure greeting only
        core = raw.rstrip("？?！!。. ")
        if ("，" in core or "," in core) and len(core) > 6:
            return False
        if any(k in core for k in ("怎么", "什么", "如何", "哪里", "为何", "为什么", "制度", "流程", "天气")):
            return False
    key = _normalize(raw)
    if key in _EXACT or raw.strip() in _EXACT:
        return True
    for pat in _PATTERNS:
        if pat.match(raw.strip()):
            return True
    return False


def canned_chitchat_reply(message: str) -> str:
    """Fixed short reply — no LLM / no retrieval."""
    q = _normalize(message)
    raw = (message or "").strip()
    if q in {"谢谢", "谢谢你", "谢谢您", "多谢", "感谢", "thanks", "thank you"} or raw.startswith("谢谢"):
        return "不客气，有问题随时问我。"
    if q in {"再见", "拜拜", "回见", "bye"} or raw.startswith(("再见", "拜拜")):
        return "再见，下次见。"
    if q in {"好的", "嗯", "哦", "收到", "ok"}:
        return "好的。"
    if q in {"在吗", "在不在"}:
        return "在的，请直接说你的问题。"
    return "你好！我是劲脑助手，可以帮你查制度与资料，直接提问即可。"
