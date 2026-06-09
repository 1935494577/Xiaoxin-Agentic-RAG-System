"""
企业知识库助手 — 导航入口。

本页: python -m streamlit run frontend/streamlit_app.py --server.port 8501
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
    page_title="企业知识库助手",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": None},
)

inject_app_css()
_scom = load_streamlit_common(_FRONT)
if hasattr(_scom, "sync_api_base_session"):
    _scom.sync_api_base_session()
mount_app_logo(_scom.get_api_base(), _scom.get_api_auth_headers())

pages = {
    "程序与配置": [
        st.Page("pages/application.py", title="RAG 对话", default=True),
        st.Page("pages/ingest.py", title="数据入库"),
        st.Page("pages/processing_config.py", title="数据处理工具"),
        st.Page("pages/vector_store_config.py", title="向量库设置"),
    ],
    "模型接入": [
        st.Page("pages/model_config.py", title="模型设置"),
    ],
    "使用教程": [
        st.Page("pages/tutorial.py", title="使用操作教程"),
    ],
}

st.navigation(pages, position="sidebar").run()
