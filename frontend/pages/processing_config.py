"""数据处理工具配置（管理员）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

_FRONT = Path(__file__).resolve().parent.parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
from _bootstrap import load_streamlit_common  # noqa: E402
from page_init import init_app_page  # noqa: E402

scom = load_streamlit_common(_FRONT)


def _fetch_tools(api_base: str) -> dict[str, Any] | None:
    try:
        with scom.http_client(api_base, timeout=10.0) as c:
            r = c.get("/config/processing-tools")
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
    init_app_page(api_base, auth, prof_data, check_model_status=False)

    st.title("数据处理工具")
    st.caption("入库时按文件类型选择解析/清洗工具；已清洗模式可启用大模型自动选工具。")

    data = _fetch_tools(api_base)
    if not data:
        st.error("无法加载工具配置，请确认 API 已启动。")
        return

    use_llm = st.toggle("启用大模型选工具（LangChain bind_tools）", value=bool(data.get("use_llm_router", True)))

    st.subheader("工具开关")
    tools = data.get("tools") or []
    toggles: dict[str, bool] = {}
    for row in tools:
        tid = str(row.get("id") or "")
        label = str(row.get("label") or tid)
        toggles[tid] = st.checkbox(label, value=bool(row.get("enabled", True)), key=f"tool_{tid}")

    if st.button("保存配置", type="primary"):
        body = {
            "use_llm_router": use_llm,
            "tools": {tid: {"enabled": val} for tid, val in toggles.items()},
        }
        try:
            with scom.http_client(api_base) as c:
                r = c.put("/config/processing-tools", json=body)
            if r.status_code == 200:
                st.success("已保存。后续入库将按新配置执行。")
            else:
                st.error(r.text[:500])
        except (httpx.ConnectError, httpx.TimeoutException):
            st.error(scom.SERVICE_UNAVAILABLE)

    with st.expander("扩展名 → 解析工具（只读）"):
        st.json(data.get("extension_map") or {})


if __name__ == "__main__":
    main()
