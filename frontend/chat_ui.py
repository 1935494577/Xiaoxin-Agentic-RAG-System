"""Enterprise chat panel — single HTML blob, no split wrapper divs."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import streamlit as st

from ui_theme import DEPT_AVATAR_PATH, _file_data_url
from user_profile import get_user_display_name, user_avatar_initial

_ASSISTANT_NAME = "企业知识库助手"


def _avatar_src() -> str | None:
    return _file_data_url(DEPT_AVATAR_PATH)


def sanitize_assistant_display(content: str) -> str:
    """Remove internal citation footers and inline ref markers from user-visible text."""
    text = (content or "").strip()
    if "\n\n引用:" in text:
        text = text.split("\n\n引用:")[0].strip()
    if "\n引用:" in text:
        text = text.split("\n引用:")[0].strip()
    text = re.sub(r"（来源\[.+?\][、\[\]0-9\s]*）", "", text)
    text = re.sub(r"\(来源\[.+?\][^\)]*\)", "", text)
    return text.strip()


def friendly_source_labels(meta: dict[str, Any] | None) -> list[str]:
    if not meta:
        return []
    refs = meta.get("source_refs") or []
    labels: list[str] = []
    seen: set[str] = set()
    for r in refs:
        if isinstance(r, dict):
            raw = str(r.get("source") or "").strip()
        else:
            raw = str(r).strip()
        if not raw:
            continue
        name = Path(raw.replace("\\", "/")).name or raw
        if name not in seen:
            seen.add(name)
            labels.append(name)
    if not labels:
        for s in meta.get("sources") or []:
            raw = str(s).strip()
            if raw and raw not in seen:
                seen.add(raw)
                labels.append(raw[:80])
    return labels[:6]


def _rich_text_html(text: str, *, markdown: bool = False) -> str:
    raw = sanitize_assistant_display(text)
    if not markdown:
        return html.escape(raw).replace("\n", "<br/>")

    parts: list[str] = []
    list_open = False
    for line in raw.split("\n"):
        stripped = line.strip()
        if not stripped:
            if list_open:
                parts.append("</ul>")
                list_open = False
            continue
        esc = html.escape(stripped)
        esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc)
        if stripped.startswith("- ") or stripped.startswith("• "):
            if not list_open:
                parts.append('<ul class="chat-md-list">')
                list_open = True
            item = esc[2:] if stripped.startswith("- ") else esc[2:]
            parts.append(f"<li>{item}</li>")
        else:
            if list_open:
                parts.append("</ul>")
                list_open = False
            parts.append(f"<p>{esc}</p>")
    if list_open:
        parts.append("</ul>")
    return "".join(parts) or html.escape(raw).replace("\n", "<br/>")


def _source_chips_html(meta: dict[str, Any] | None) -> str:
    labels = friendly_source_labels(meta)
    if not labels:
        return ""
    chips = "".join(f'<span class="source-chip">{html.escape(l)}</span>' for l in labels)
    return f'<div class="source-chips"><span class="source-label">参考文档</span>{chips}</div>'


def _bubble_html(
    role: str,
    name: str,
    content: str,
    *,
    meta: dict[str, Any] | None = None,
    markdown: bool = False,
) -> str:
    align = "user" if role == "user" else "assistant"
    avatar = _avatar_src()
    if avatar:
        avatar_html = f'<img class="chat-avatar-img" src="{avatar}" alt=""/>'
    else:
        avatar_html = (
            f'<div class="chat-avatar-fallback">{html.escape(user_avatar_initial())}</div>'
            if role == "user"
            else '<div class="chat-avatar-fallback bot">助</div>'
        )
    body = _rich_text_html(content, markdown=markdown and role == "assistant")
    chips = _source_chips_html(meta) if role == "assistant" else ""
    return (
        f'<div class="chat-row chat-row-{align}">'
        f'<div class="chat-avatar">{avatar_html}</div>'
        f'<div class="chat-col">'
        f'<div class="chat-name">{html.escape(name)}</div>'
        f'<div class="chat-bubble">{body}{chips}</div>'
        f"</div></div>"
    )


def message_bubble_html(role: str, name: str, content: str, *, meta: dict[str, Any] | None = None) -> str:
    return _bubble_html(role, name, content, meta=meta, markdown=(role == "assistant"))


def welcome_html(tagline: str) -> str:
    text = (tagline or "把文档放进知识库，用自然语言提问；无需编写代码。").strip()
    return _bubble_html("assistant", _ASSISTANT_NAME, text, markdown=False)


def build_messages_html(
    messages: list[dict[str, Any]],
    *,
    show_welcome: bool,
    tagline: str,
) -> str:
    parts: list[str] = ['<div class="chat-card"><div class="chat-messages"><div class="chat-messages-inner">']
    if show_welcome and not messages:
        parts.append(welcome_html(tagline))
    for m in messages:
        role = str(m.get("role") or "assistant")
        name = get_user_display_name() if role == "user" else _ASSISTANT_NAME
        parts.append(
            _bubble_html(
                role,
                name,
                str(m.get("content") or ""),
                meta=m.get("meta"),
                markdown=(role == "assistant"),
            )
        )
    parts.append("</div></div></div>")
    return "".join(parts)


def render_chat_panel(
    messages: list[dict[str, Any]],
    *,
    show_welcome: bool,
    tagline: str,
    title: str,
    append_html: str = "",
) -> None:
    header = (
        f'<div class="chat-card">'
        f'<div class="chat-card-header"><h1 class="chat-title">{html.escape(title)}</h1></div>'
        f'<div class="chat-messages"><div class="chat-messages-inner">'
    )
    inner: list[str] = [header]
    if show_welcome and not messages:
        inner.append(welcome_html(tagline))
    for m in messages:
        role = str(m.get("role") or "assistant")
        name = get_user_display_name() if role == "user" else _ASSISTANT_NAME
        inner.append(
            _bubble_html(
                role,
                name,
                str(m.get("content") or ""),
                meta=m.get("meta"),
                markdown=(role == "assistant"),
            )
        )
    if append_html:
        inner.append(append_html)
    inner.append("</div></div></div>")
    st.markdown("".join(inner), unsafe_allow_html=True)


def render_streaming_assistant(placeholder, content: str, *, phase: str = "") -> None:
    hint = ""
    if phase == "retrieving":
        hint = '<span class="chat-phase">正在检索知识库…</span>'
    elif phase == "generating" and not content:
        hint = '<span class="chat-phase">正在组织回答…</span>'
    body = _rich_text_html(content, markdown=True) if content else ""
    cursor = '<span class="chat-cursor">▌</span>' if content and phase != "retrieving" else ""
    avatar = _avatar_src()
    avatar_html = (
        f'<img class="chat-avatar-img" src="{avatar}" alt=""/>'
        if avatar
        else '<div class="chat-avatar-fallback bot">助</div>'
    )
    html_block = (
        '<div class="chat-row chat-row-assistant">'
        f'<div class="chat-avatar">{avatar_html}</div>'
        '<div class="chat-col">'
        f'<div class="chat-name">{html.escape(_ASSISTANT_NAME)}</div>'
        f'<div class="chat-bubble">{hint}{body}{cursor}</div>'
        "</div></div>"
    )
    placeholder.markdown(html_block, unsafe_allow_html=True)


def user_facing_error(raw: str) -> str:
    text = (raw or "").strip()
    lower = text.lower()
    if "api key" in lower or "未配置" in text:
        return "服务暂不可用，请联系管理员配置模型接入。"
    if "向量库" in text or "向量维度不一致" in text or "not aligned" in lower:
        return "知识库索引与当前嵌入模型不匹配，请在「向量库设置」中新建或切换匹配的向量库，并重新入库。"
        return "网络响应超时，请稍后重试。"
    if "http" in lower and any(c.isdigit() for c in text[:20]):
        return "请求未能完成，请稍后重试。"
    if len(text) > 200:
        return "处理出现问题，请稍后重试。"
    return text or "处理出现问题，请稍后重试。"
