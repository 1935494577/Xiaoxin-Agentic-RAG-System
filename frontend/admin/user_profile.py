"""Sidebar user profile — bottom bar opens settings popover."""

from __future__ import annotations

import hashlib

import streamlit as st

from ui_theme import DEPT_AVATAR_PATH, DEPT_LABELS, DEPT_OPTIONS, _file_data_url

_DEFAULT_NAME = "你"
_DEFAULT_DEPT = "技术"


def init_user_profile_state() -> None:
    st.session_state.setdefault("user_display_name", _DEFAULT_NAME)
    st.session_state.setdefault("ingest_dept", _DEFAULT_DEPT)
    if st.session_state.get("ingest_dept") not in DEPT_OPTIONS:
        st.session_state.ingest_dept = _DEFAULT_DEPT


def get_user_display_name() -> str:
    name = str(st.session_state.get("user_display_name") or "").strip()
    return name or _DEFAULT_NAME


def get_dept_code() -> str:
    dept = str(st.session_state.get("ingest_dept") or "").strip()
    return dept if dept in DEPT_OPTIONS else _DEFAULT_DEPT


def get_user_id() -> str:
    """Stable user id for session storage; explicit override wins over derived id."""
    explicit = str(st.session_state.get("user_id") or "").strip()
    if explicit:
        return explicit[:128]
    seed = f"{get_dept_code()}|{get_user_display_name()}"
    derived = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    st.session_state["_derived_user_id"] = derived
    return derived


def get_dept_display_label() -> str:
    return DEPT_LABELS.get(get_dept_code(), get_dept_code())


def user_avatar_initial() -> str:
    name = get_user_display_name()
    if not name or name == _DEFAULT_NAME:
        return "你"
    return name[0].upper()


def _inject_profile_popover_css() -> None:
    avatar = _file_data_url(DEPT_AVATAR_PATH)
    avatar_rule = ""
    if avatar:
        avatar_rule = f"""
section[data-testid="stSidebarUserContent"] [data-testid="stPopover"] button::before {{
  content: "";
  position: absolute;
  left: 0.7rem;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: url("{avatar}") center/cover no-repeat;
  border: 2px solid #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}}
section[data-testid="stSidebarUserContent"] [data-testid="stPopover"] button {{
  padding-left: 3.15rem !important;
  min-height: 2.75rem !important;
  position: relative !important;
}}
"""
    st.markdown(f"<style>{avatar_rule}</style>", unsafe_allow_html=True)


def render_sidebar_profile_editor() -> None:
    init_user_profile_state()
    name = get_user_display_name()
    dept = get_dept_display_label()
    _inject_profile_popover_css()

    with st.sidebar.popover(f"{name} · {dept}", use_container_width=True):
        st.markdown("**个人设置**")
        st.text_input("姓名", key="user_display_name", max_chars=32, placeholder="输入你的姓名")
        st.selectbox(
            "部门",
            DEPT_OPTIONS,
            format_func=lambda x: DEPT_LABELS.get(x, x),
            key="ingest_dept",
            help="与入库文档归属部门一致时，检索结果更准确。",
        )
        st.text_input(
            "用户 ID",
            key="user_id",
            max_chars=128,
            placeholder="留空则按姓名+部门自动生成",
            help="对话历史按用户 ID 存储；修改后需重新选择会话。",
        )
