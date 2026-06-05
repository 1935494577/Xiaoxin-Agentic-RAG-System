"""Ingest mode normalization."""

from __future__ import annotations

PRE_CLEANED = "pre_cleaned"
UNCLEANED = "uncleaned"


def normalize_ingest_mode(mode: str | None) -> str:
    """
    pre_cleaned — 已清洗数据：仅解析入库，不做脱敏/去水印等深度清洗。
    uncleaned — 未清洗数据：走完整工具链（含可选 LLM 路由）。

    Legacy aliases: raw -> pre_cleaned, cleaned -> uncleaned.
    """
    m = (mode or "").strip().lower()
    if m in (PRE_CLEANED, "raw"):
        return PRE_CLEANED
    if m in (UNCLEANED, "cleaned"):
        return UNCLEANED
    return PRE_CLEANED
