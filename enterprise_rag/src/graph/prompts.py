"""Graph RAG answer prompts."""

from __future__ import annotations


def graph_kb_system_extra() -> str:
    return (
        "【Graph RAG 模式】用户问题涉及实体关系链。回答时：\n"
        "1. 明确列出相关对象及其关系（谁依赖谁、谁影响谁、谁与谁关联）。\n"
        "2. 若资料中有审批链/上下游，按链路顺序说明。\n"
        "3. 关系不确定时标注「资料未明确」，不要编造关系。"
    )
