"""Prepare tool outputs for LLM context: structure compress → optional LLM condense → hard cap."""

from __future__ import annotations

import re
from typing import Any

from config import settings

_CONDENSE_SYSTEM = (
    "你是工具结果提炼器。根据用户问题，从工具原始输出中提取直接相关的事实。"
    "保留日期、数字、地点、专有名词；不要编造；不要寒暄；用简洁中文要点输出。"
    "若原始输出与问题无关，只回复：工具未返回相关信息。"
)


def _last_user_question(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user" and msg.get("content"):
            return str(msg["content"]).strip()
    return ""


def compress_web_search_output(text: str, *, max_results: int = 3, snippet_chars: int = 200) -> str:
    """Keep Tavily summary + top-N results with shorter snippets."""
    if "搜索「" not in text:
        return text

    lines = text.splitlines()
    header = next((ln for ln in lines if ln.startswith("搜索「")), "")
    summary = ""
    for ln in lines:
        if ln.startswith("【摘要】"):
            summary = ln
            break

    blocks: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        if re.match(r"^\d+\.\s", ln):
            if current:
                blocks.append(current)
            current = [ln]
        elif current:
            current.append(ln)
    if current:
        blocks.append(current)

    if not blocks and not summary:
        return text

    out: list[str] = []
    if header:
        out.append(header)
        out.append("")
    if summary:
        out.append(summary)
        out.append("")

    shown = blocks[:max_results]
    for block in shown:
        compact: list[str] = []
        for i, ln in enumerate(block):
            stripped = ln.strip()
            if i == 0:
                compact.append(ln)
            elif stripped.startswith("链接:"):
                compact.append(ln)
            elif stripped and not stripped.startswith("链接:"):
                prefix = ln[: len(ln) - len(ln.lstrip())]
                body = stripped
                if len(body) > snippet_chars:
                    body = body[:snippet_chars].rstrip() + "…"
                compact.append(f"{prefix}{body}")
            else:
                compact.append(ln)
        out.extend(compact)
        out.append("")

    omitted = len(blocks) - len(shown)
    if omitted > 0:
        out.append(f"（另有 {omitted} 条搜索结果未列入上下文，模型应依据以上要点作答）")

    return "\n".join(out).strip()


def condense_with_llm(
    client: Any,
    *,
    model: str,
    question: str,
    tool_name: str,
    output: str,
    temperature: float = 0.1,
    max_tokens: int = 900,
) -> str:
    user = (
        f"用户问题：{question}\n"
        f"工具名称：{tool_name}\n\n"
        f"工具原始输出：\n{output}\n\n"
        "请提炼与问题相关的要点（不超过 800 字）："
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _CONDENSE_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    text = (resp.choices[0].message.content or "").strip()
    return text or output


def truncate_tool_output_for_llm(output: str, *, max_chars: int | None = None) -> str:
    text = output or ""
    limit = max_chars if max_chars is not None else int(settings.tool_llm_context_max_chars)
    limit = max(256, limit)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n…（上下文长度上限，原长 {len(text)} 字）"


def prepare_tool_content_for_llm(
    output: str,
    *,
    tool_name: str,
    question: str = "",
    client: Any | None = None,
    condense_model: str | None = None,
    condense_enabled: bool | None = None,
) -> str:
    """
    Full tool output stays in trace/SSE for UI.
    This function builds what the answer model reads in the tool role message.
    """
    text = (output or "").strip()
    if not text:
        return text

    min_chars = int(settings.tool_llm_condense_min_chars)
    if len(text) <= min_chars:
        return text

    working = text
    if tool_name == "web_search":
        working = compress_web_search_output(working)

    use_condense = (
        condense_enabled
        if condense_enabled is not None
        else bool(settings.tool_output_condense_enabled)
    )
    if (
        use_condense
        and client is not None
        and condense_model
        and len(working) > min_chars
    ):
        try:
            working = condense_with_llm(
                client,
                model=condense_model,
                question=question,
                tool_name=tool_name,
                output=working,
            )
        except Exception:
            pass

    return truncate_tool_output_for_llm(working)
