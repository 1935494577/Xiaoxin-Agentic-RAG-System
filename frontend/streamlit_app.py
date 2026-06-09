"""
企业知识库 — 管理后台入口（对话在 Chat SPA）。

本页: python -m streamlit run frontend/streamlit_app.py --server.port 8501
主入口（对话）: http://127.0.0.1:8502
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_FRONT = Path(__file__).resolve().parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))

from _bootstrap import load_streamlit_common  # noqa: E402
from ui_theme import inject_app_css, mount_app_logo  # noqa: E402

st.set_page_config(
    page_title="企业知识库管理",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": None},
)

inject_app_css()
_scom = load_streamlit_common(_FRONT)
if hasattr(_scom, "sync_api_base_session"):
    _scom.sync_api_base_session()
mount_app_logo(_scom.get_api_base(), _scom.get_api_auth_headers())

pages = [
    st.Page("pages/ingest.py", title="数据入库", url_path="ingest", default=True),
    st.Page("pages/processing_config.py", title="数据处理", url_path="processing"),
    st.Page("pages/vector_store_config.py", title="向量库", url_path="vector_store"),
    st.Page("pages/chat_memory_config.py", title="对话记忆", url_path="memory"),
    st.Page("pages/model_config.py", title="模型", url_path="models"),
    st.Page("pages/trace_config.py", title="链路 Trace", url_path="trace"),
    st.Page("pages/tutorial.py", title="教程", url_path="tutorial"),
]

st.navigation(pages, position="hidden").run()
