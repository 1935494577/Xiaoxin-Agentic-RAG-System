"""Trace / observability settings — LangSmith status."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

_FRONT = Path(__file__).resolve().parent.parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
from _bootstrap import load_streamlit_common  # noqa: E402
from page_init import init_app_page  # noqa: E402

scom = load_streamlit_common(_FRONT)


def _fetch_trace_status(api_base: str) -> dict[str, Any] | None:
    try:
        with scom.http_client(api_base, timeout=10.0) as c:
            r = c.get("/debug/trace-status")
            if r.status_code == 200:
                return r.json()
    except Exception:
        return None
    return None


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    prof_data = scom.fetch_model_profiles(api_base)
    init_app_page(api_base, auth, prof_data, check_model_status=False, nav_id="trace")

    st.title("链路 Trace")
    st.caption("LangSmith 云端追踪；修改 .env 后需重启 API。")

    trace = _fetch_trace_status(api_base)
    if trace:
        c1, c2, c3 = st.columns(3)
        c1.metric("LangSmith", "已启用" if trace.get("langsmith_enabled") else "未启用")
        c2.metric("本地 JSONL", "已启用" if trace.get("local_enabled") else "未启用")
        c3.metric("Trace 活跃", "是" if trace.get("active") else "否")
        if trace.get("project"):
            st.info(f"LangSmith 项目：`{trace['project']}`")
    else:
        st.warning("无法读取 /debug/trace-status，请确认 API 已启动。")

    st.divider()
    st.subheader("环境变量（需重启 API）")
    st.code(
        "LANGCHAIN_TRACING_V2=true\nLANGCHAIN_API_KEY=lsv2_...\n"
        "LANGCHAIN_PROJECT=enterprise-rag",
        language="ini",
    )


if __name__ == "__main__":
    main()
