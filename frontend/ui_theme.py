"""Shared UI theme, branding helpers, and layout CSS."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

_ASSETS = Path(__file__).resolve().parent / "assets"
COMPANY_LOGO_PATH = _ASSETS / "company_logo.png"
DEPT_AVATAR_PATH = _ASSETS / "dept_avatar.png"

DEFAULT_UI: dict[str, Any] = {
    "logo_en": "JNAO",
    "logo_cn": "劲脑",
    "has_logo_image": False,
    "app_title": "企业知识库助手",
    "app_tagline": "把文档放进知识库，用自然语言提问；无需编写代码。",
    "suggested_questions": [
        "1-3年级超脑阅读要求是什么？",
        "把文档放进知识库后如何提问？",
        "支持哪些文件格式入库？",
    ],
    "supported_upload_extensions": ["txt", "md", "pdf", "docx", "html"],
    "supported_upload_label": "TXT · MD · PDF · DOCX · HTML",
}

DEPT_OPTIONS = ["general", "技术", "市场", "人事", "财务"]
DEPT_LABELS = {
    "general": "通用",
    "技术": "技术",
    "市场": "市场",
    "人事": "人事",
    "财务": "财务",
}
PERM_OPTIONS = ["public", "1", "internal", "confidential"]
PERM_LABELS = {
    "public": "公开",
    "1": "内部",
    "internal": "内部",
    "confidential": "机密",
}


def inject_app_css() -> None:
    st.markdown(
        """
<style>
:root {
  --brand-primary: #1565c0;
  --brand-accent: #f5b800;
  --surface: #ffffff;
  --surface-muted: #f4f6f9;
  --border: #e4e8ef;
  --text: #1a1d21;
  --text-muted: #5f6b7a;
  --radius-lg: 16px;
  --radius-md: 12px;
  --shadow-sm: 0 1px 3px rgba(16, 24, 40, 0.06);
}

/* Main layout — compact, centered */
.main .block-container {
  padding-top: 1.25rem;
  padding-bottom: 2rem;
  max-width: 820px;
}
header[data-testid="stHeader"] { background: transparent; border: none; }
#MainMenu, footer { visibility: hidden; height: 0; }

/* Sidebar logo — above navigation */
[data-testid="stSidebar"] [data-testid="stLogo"] {
  padding: 0.65rem 0.75rem 0.85rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.15rem;
}
[data-testid="stSidebar"] [data-testid="stLogo"] img {
  max-height: 36px; width: auto; object-fit: contain;
}
section[data-testid="stSidebar"] > div:first-child {
  display: flex; flex-direction: column; min-height: 100%;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
  order: 10; margin-top: 0.15rem; flex: 0 0 auto;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
  order: 90; display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div {
  display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
  border-radius: 8px; font-size: 0.92rem;
}
.sidebar-spacer { flex: 1 1 auto; min-height: 1rem; order: 50; width: 100%; }
section[data-testid="stSidebarUserContent"] [data-testid="stPopover"] {
  order: 99; margin-top: auto; width: 100%;
  padding-top: 0.65rem; border-top: 1px solid var(--border);
}
section[data-testid="stSidebarUserContent"] [data-testid="stPopover"] button {
  width: 100% !important; justify-content: flex-start !important;
  background: var(--surface-muted) !important; color: var(--text) !important;
  border: none !important; border-radius: var(--radius-md) !important;
  font-size: 0.86rem !important; font-weight: 500 !important;
  padding: 0.65rem 0.85rem !important; box-shadow: none !important;
}
section[data-testid="stSidebarUserContent"] [data-testid="stPopover"] button:hover {
  background: #e8edf3 !important;
}
section[data-testid="stSidebarUserContent"] [data-testid="stPopoverBody"] {
  padding: 0.85rem 1rem !important; min-width: 240px;
}

/* Chat card — single panel, no empty min-height block */
.chat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  margin-bottom: 0.5rem;
}
.chat-card-header {
  padding: 1rem 1.25rem 0.75rem;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, #fafbfc 0%, #fff 100%);
}
.chat-title {
  margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--text);
  letter-spacing: 0.01em;
}
.chat-messages { padding: 1rem 1.25rem 0.5rem; background: var(--surface-muted); }
.chat-messages-inner { display: flex; flex-direction: column; gap: 1rem; }

.chat-row { display: flex; align-items: flex-start; gap: 0.6rem; max-width: 100%; }
.chat-row-user { flex-direction: row-reverse; margin-left: auto; max-width: 82%; }
.chat-row-assistant { margin-right: auto; max-width: 95%; }
.chat-avatar { flex-shrink: 0; }
.chat-avatar-img {
  width: 32px; height: 32px; border-radius: 50%; object-fit: cover; display: block;
  border: 2px solid #fff; box-shadow: var(--shadow-sm);
}
.chat-avatar-fallback {
  width: 32px; height: 32px; border-radius: 50%; background: var(--brand-primary); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700;
}
.chat-avatar-fallback.bot { background: #0d47a1; }
.chat-col { min-width: 0; flex: 1; }
.chat-row-user .chat-col { display: flex; flex-direction: column; align-items: flex-end; }
.chat-name { font-size: 0.78rem; color: var(--text-muted); margin-bottom: 0.2rem; font-weight: 600; }
.chat-bubble {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: 0.8rem 1rem;
  color: var(--text); font-size: 0.94rem; line-height: 1.6; word-break: break-word;
  box-shadow: var(--shadow-sm);
}
.chat-row-user .chat-bubble { background: #eef3fb; border-color: #d6e4f7; }
.chat-bubble p { margin: 0 0 0.45rem 0; }
.chat-bubble p:last-child { margin-bottom: 0; }
.chat-md-list { margin: 0.35rem 0 0.5rem 1.1rem; padding: 0; }
.chat-md-list li { margin-bottom: 0.35rem; }
.chat-phase { color: var(--text-muted); font-size: 0.86rem; font-style: italic; }
.chat-cursor { color: var(--brand-primary); animation: chat-blink 1s step-end infinite; }
@keyframes chat-blink { 50% { opacity: 0; } }

.source-chips { margin-top: 0.75rem; padding-top: 0.65rem; border-top: 1px dashed var(--border); }
.source-label { font-size: 0.75rem; color: var(--text-muted); margin-right: 0.4rem; }
.source-chip {
  display: inline-block; margin: 0.15rem 0.25rem 0 0; padding: 0.15rem 0.55rem;
  background: #eef2f7; border-radius: 999px; font-size: 0.74rem; color: #4a5568;
}

/* Suggestions */
.suggest-wrap { margin: 0.35rem 0 0.75rem 0; padding: 0 0.15rem; }
.suggest-wrap .stButton > button {
  border-radius: 999px !important; background: var(--surface) !important;
  color: var(--text) !important; border: 1px solid var(--border) !important;
  font-size: 0.82rem !important; padding: 0.4rem 0.75rem !important;
  box-shadow: none !important; transition: background 0.15s;
}
.suggest-wrap .stButton > button:hover {
  background: var(--surface-muted) !important; border-color: #c5d0de !important;
}

/* Chat input — attached to card */
div[data-testid="stChatInput"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 0.65rem 0.85rem !important;
  box-shadow: var(--shadow-sm) !important;
  max-width: 820px;
}
div[data-testid="stChatInput"] > div {
  background: var(--surface-muted) !important;
  border-radius: 999px !important; border: 1px solid var(--border) !important;
}
div[data-testid="stChatInput"] textarea {
  border-radius: 999px !important; background: transparent !important; font-size: 0.92rem !important;
}
div[data-testid="stChatInput"] button {
  background: var(--brand-accent) !important; color: #1a1d21 !important;
  border-radius: 50% !important; min-width: 2.2rem !important; min-height: 2.2rem !important;
}

/* Orphan stream rows align with card */
.main .chat-row-assistant, .main .chat-row-user {
  max-width: 820px; margin-left: auto; margin-right: auto;
  padding-left: 1.25rem; padding-right: 1.25rem;
}

/* Ingest page */
.page-header-compact { margin: 0 0 1rem 0; }
.page-header-compact h1 {
  margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--text);
}
.page-header-compact p { margin: 0.25rem 0 0; color: var(--text-muted); font-size: 0.88rem; }
.ingest-panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 1.15rem 1.25rem 1.25rem;
  box-shadow: var(--shadow-sm);
}
.ingest-panel h3 { margin-top: 0; font-size: 1rem; font-weight: 600; color: var(--text); }
.ingest-upload-label { margin: 0; font-size: 0.92rem; font-weight: 600; color: var(--text); }
.ingest-formats { color: var(--text-muted); font-size: 0.84rem; font-weight: 400; }
div[data-testid="stFileUploader"] section {
  border: 2px dashed #cfd8e3 !important; border-radius: var(--radius-md) !important;
  background: var(--surface-muted) !important; min-height: 140px !important;
}

/* Admin: model status (model settings page only) */
.model-status-wrap {
  position: fixed; top: 0.65rem; right: 1rem; z-index: 999;
  display: flex; align-items: center; gap: 0.4rem;
  background: var(--surface); padding: 0.3rem 0.7rem; border-radius: 999px;
  border: 1px solid var(--border); font-size: 0.78rem; color: var(--text-muted);
  box-shadow: var(--shadow-sm);
}
.model-status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
</style>
        """,
        unsafe_allow_html=True,
    )


def fetch_ui_config(api_base: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        with httpx.Client(base_url=api_base.rstrip("/"), timeout=10.0, headers=headers or None) as c:
            r = c.get("/config/ui")
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return dict(DEFAULT_UI)


def _file_data_url(path: Path) -> str | None:
    if not path.is_file():
        return None
    mime = "image/png"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif path.suffix.lower() == ".webp":
        mime = "image/webp"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _logo_image_data_url(api_base: str, headers: dict[str, str] | None) -> str | None:
    """Fetch uploaded logo bytes. Call only when has_logo_image is true."""
    try:
        with httpx.Client(base_url=api_base.rstrip("/"), timeout=5.0, headers=headers or None) as c:
            r = c.get("/config/ui/logo")
            if r.status_code != 200:
                return None
            mime = r.headers.get("content-type", "image/png")
            b64 = base64.b64encode(r.content).decode("ascii")
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def resolve_app_logo_path(api_base: str | None = None, headers: dict[str, str] | None = None) -> str | None:
    """Local bundled logo by default; API logo only when uploaded (has_logo_image)."""
    if api_base:
        cfg = fetch_ui_config(api_base, headers)
        if cfg.get("has_logo_image"):
            uploaded = _logo_image_data_url(api_base, headers)
            if uploaded:
                return uploaded
    if COMPANY_LOGO_PATH.is_file():
        return str(COMPANY_LOGO_PATH.resolve())
    return None


def render_sidebar_brand(cfg: dict[str, Any], api_base: str, headers: dict[str, str] | None = None) -> None:
    """Legacy inline brand (prefer mount_app_logo in streamlit_app.py)."""
    img = _logo_image_data_url(api_base, headers) if cfg.get("has_logo_image") else None
    if not img:
        img = _file_data_url(COMPANY_LOGO_PATH)
    if img:
        st.sidebar.markdown(
            f'<div class="jnao-brand"><img class="logo-img" src="{img}" alt="JNAO"/></div>',
            unsafe_allow_html=True,
        )
    else:
        logo_en = str(cfg.get("logo_en") or "JNAO")
        st.sidebar.markdown(
            f'<div class="jnao-brand"><span class="logo-en">{logo_en}</span></div>',
            unsafe_allow_html=True,
        )


def mount_app_logo(api_base: str | None = None, headers: dict[str, str] | None = None) -> None:
    """Place logo above sidebar navigation (Streamlit st.logo). Runs once per session."""
    if st.session_state.get("_app_logo_mounted"):
        return
    img = resolve_app_logo_path(api_base, headers)
    if not img:
        st.session_state["_app_logo_mounted"] = True
        return
    try:
        st.logo(img)
    except Exception:
        if COMPANY_LOGO_PATH.is_file():
            try:
                st.logo(str(COMPANY_LOGO_PATH.resolve()))
            except Exception:
                pass
    st.session_state["_app_logo_mounted"] = True


def render_sidebar_user(display_name: str, department: str) -> None:
    name = (display_name or "你的名字").strip()
    dept = (department or "部门").strip()
    avatar = _file_data_url(DEPT_AVATAR_PATH)
    if avatar:
        avatar_html = f'<img class="avatar-img" src="{avatar}" alt="部门"/>'
    else:
        initial = name[0].upper() if name else "U"
        avatar_html = f'<div class="avatar">{initial}</div>'
    st.sidebar.markdown(
        f'<div class="sidebar-user">{avatar_html}'
        f'<div class="label">{name} · {dept}</div></div>',
        unsafe_allow_html=True,
    )


def fetch_model_connection_status(
    api_base: str,
    headers: dict[str, str] | None,
    profile_id: str | None,
    force_env: bool,
    *,
    quick: bool = True,
    force_check: bool = False,
) -> bool:
    try:
        params: dict[str, str | bool] = {"force_env_llm": force_env, "quick": quick, "force_check": force_check}
        if profile_id:
            params["profile_id"] = profile_id
        with httpx.Client(base_url=api_base.rstrip("/"), timeout=5.0, headers=headers or None) as c:
            r = c.get("/config/model-profiles/connection-status", params=params)
            if r.status_code == 200:
                return bool(r.json().get("connected"))
    except Exception:
        pass
    return False


def render_model_status_light(connected: bool) -> None:
    color = "#4caf50" if connected else "#f44336"
    label = "模型已连接" if connected else "模型未连接"
    st.markdown(
        f'<div class="model-status-wrap" title="{label}">'
        f'<span class="model-status-dot" style="background:{color};"></span>'
        f'<span>{label}</span></div>',
        unsafe_allow_html=True,
    )


def render_minimal_sidebar(cfg: dict[str, Any], api_base: str, headers: dict[str, str] | None = None) -> None:
    """侧边栏底部用户条（Logo 在 streamlit_app 中置于导航上方）。"""
    from user_profile import render_sidebar_profile_editor

    inject_app_css()
    st.sidebar.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    render_sidebar_profile_editor()


def render_page_header(cfg: dict[str, Any], *, compact: bool = False) -> None:
    title = str(cfg.get("app_title") or "企业知识库助手")
    tagline = str(cfg.get("app_tagline") or "")
    if compact:
        tagline_html = f"<p>{tagline}</p>" if tagline else ""
        st.markdown(
            f'<div class="page-header-compact"><h1>{title}</h1>{tagline_html}</div>',
            unsafe_allow_html=True,
        )
        return
    st.markdown(f'<p class="app-hero-title">{title}</p>', unsafe_allow_html=True)
    if tagline:
        st.markdown(f'<p class="app-hero-tagline">{tagline}</p>', unsafe_allow_html=True)
