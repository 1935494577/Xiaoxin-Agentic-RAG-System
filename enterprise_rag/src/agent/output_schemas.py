"""Structured output templates for content / sales channels (企微、视频号、抖音等)."""

from __future__ import annotations

from typing import Any

OUTPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "selling_points": {
        "label": "卖点清单",
        "description": "面向家长的课程/脑力训练卖点，突出提分与差异",
        "channels": ["wecom", "wechat", "miniprogram", "channels", "douyin"],
        "instruction": (
            "【输出格式 · 卖点清单】严格按以下 Markdown 结构输出，仅依据参考资料：\n"
            "## 核心定位（1 句）\n"
            "## 家长痛点 → 价值（3–5 条，每条：痛点 / 我们的方案 / 预期效果）\n"
            "## 与传统培训的差异（2–3 条）\n"
            "## 行动号召（1 句，适合私聊或简介区）\n"
            "禁止编造未在资料出现的承诺、分数或疗效。"
        ),
    },
    "parent_dm_script": {
        "label": "企微 / 私聊话术",
        "description": "企业微信或微信一对一沟通脚本",
        "channels": ["wecom", "wechat"],
        "instruction": (
            "【输出格式 · 私聊话术】分三段，每段 2–4 句，口语化、可逐条发送：\n"
            "1. **开场共情**（不推销）\n"
            "2. **价值传递**（基于资料的 1–2 个具体点）\n"
            "3. **轻 CTA**（邀约体验 / 发资料 / 约沟通，不施压）\n"
            "勿使用「保证提分」等绝对化表述，除非资料原文如此。"
        ),
    },
    "short_video_script": {
        "label": "短视频口播脚本",
        "description": "视频号 / 抖音 30–60 秒口播结构",
        "channels": ["channels", "douyin"],
        "instruction": (
            "【输出格式 · 短视频脚本】总时长约 30–60 秒口播：\n"
            "| 段落 | 时长 | 口播文案 |\n"
            "|---|---|---|\n"
            "| 钩子 | 3–5s | … |\n"
            "| 要点1 | … | … |\n"
            "| 要点2 | … | … |\n"
            "| 要点3 | … | … |\n"
            "| 行动号召 | 5s | … |\n"
            "文案口语化、适合对着镜头念；事实仅来自参考资料。"
        ),
    },
    "compare_table": {
        "label": "对比表",
        "description": "两个主题 / 课程 / 方案的并排对比",
        "channels": ["all"],
        "instruction": (
            "【输出格式 · 对比表】Markdown 表格，列：维度 | A | B | 说明（可选）\n"
            "至少 5 行维度（适用对象、训练方式、周期、效果预期、注意事项等）。"
        ),
    },
    "faq_bullets": {
        "label": "FAQ 问答",
        "description": "可转发给家长的常见问答",
        "channels": ["wecom", "wechat", "miniprogram"],
        "instruction": (
            "【输出格式 · FAQ】5–8 组，每组：\n"
            "**Q：** …\n**A：** …（2–4 句，可直接复制到企微）\n"
        ),
    },
    "checklist": {
        "label": "检查清单",
        "description": "通用要点 / 注意事项清单",
        "channels": ["all"],
        "instruction": (
            "【输出格式 · 检查清单】Markdown checkbox 列表，分组标题，每组 3–7 项。"
        ),
    },
}


def list_output_schemas_public(*, channel: str | None = None) -> list[dict[str, str]]:
    ch = (channel or "all").strip().lower() or "all"
    out: list[dict[str, str]] = []
    for sid, meta in OUTPUT_SCHEMAS.items():
        channels = [str(c).lower() for c in (meta.get("channels") or ["all"])]
        if ch != "all" and "all" not in channels and ch not in channels:
            continue
        out.append(
            {
                "id": sid,
                "label": str(meta.get("label") or sid),
                "description": str(meta.get("description") or ""),
            }
        )
    return out


def get_output_schema(schema_id: str | None) -> dict[str, Any] | None:
    key = (schema_id or "").strip()
    if not key:
        return None
    row = OUTPUT_SCHEMAS.get(key)
    return dict(row) if row else None


def output_schema_instruction(schema_id: str | None) -> str:
    row = get_output_schema(schema_id)
    if not row:
        return ""
    return str(row.get("instruction") or "").strip()
