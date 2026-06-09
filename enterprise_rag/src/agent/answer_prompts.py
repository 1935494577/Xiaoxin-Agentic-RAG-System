"""System prompts and user payloads for kb vs general answering."""

from __future__ import annotations

KB_SYSTEM = (
    "你是企业知识库助手。优先依据提供的参考资料回答；"
    "可结合对话历史理解指代与上下文。"
    "若资料不足以回答，请明确说明资料不足，不要编造。"
)

KB_SYSTEM_FAST = (
    "你是企业知识库助手。依据参考资料简洁作答；"
    "资料不足请说明，不要编造。"
)

GENERAL_SYSTEM = (
    "你是企业知识库助手。当前问题未命中足够相关的内部资料，"
    "请基于通用知识与对话历史作答。"
    "不要假装引用了不存在的内部文档；必要时说明这是通用建议。"
)


def kb_system_prompt(*, fast: bool = False) -> str:
    return KB_SYSTEM_FAST if fast else KB_SYSTEM


def general_system_prompt() -> str:
    return GENERAL_SYSTEM


def kb_user_content(contexts: list[str], question: str) -> str:
    body = "\n".join(f"[{i + 1}] {t}" for i, t in enumerate(contexts))
    return f"参考资料：\n{body}\n\n用户问题：{question}"


def general_user_content(question: str) -> str:
    return f"用户问题：{question}"
