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


def _check(label: str, ok: bool) -> None:
    icon = "✅" if ok else "⬜"
    st.markdown(f"{icon} {label}")


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    prof_data = scom.fetch_model_profiles(api_base)
    init_app_page(api_base, auth, prof_data, check_model_status=False, nav_id="trace")

    st.title("链路 Trace")
    st.caption(
        "LangSmith：同步 /chat 为 LangGraph；Jnao Chat 8502 流式为 stream_rag_chat（标签 stream）。"
        "修改 .env 后需重启 API。"
    )

    trace = _fetch_trace_status(api_base)
    if not trace:
        st.warning("无法读取 /debug/trace-status，请确认 API 已启动。")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("LangSmith", "已启用" if trace.get("langsmith_enabled") else "未启用")
    c2.metric("本地 JSONL", "已启用" if trace.get("local_enabled") else "未启用")
    c3.metric("Trace 活跃", "是" if trace.get("active") else "否")

    st.subheader("LangSmith 检查项")
    _check("LANGCHAIN_TRACING_V2=true", bool(trace.get("langsmith_tracing_v2")))
    _check("LANGCHAIN_API_KEY 已配置", bool(trace.get("langsmith_configured")))
    _check("langsmith 包已安装", bool(trace.get("langsmith_package_installed")))
    if trace.get("project"):
        st.info(f"LangSmith 项目：`{trace['project']}`")

    st.subheader("本地 JSONL")
    local_path = trace.get("local_path") or ""
    st.text(f"文件路径：{local_path}")
    exists = bool(trace.get("local_file_exists"))
    count = int(trace.get("local_record_count") or 0)
    if exists:
        st.success(f"文件已存在，共 {count} 条记录。")
    else:
        st.caption("文件尚未创建（开启本地 trace 且产生对话后会自动生成）。")

    hints = trace.get("hints") or []
    if hints:
        st.subheader("待办 / 提示")
        for h in hints:
            st.markdown(f"- {h}")

    st.divider()
    with st.expander("演进路线（Agent 全链路追踪）", expanded=False):
        st.markdown(
            """
**目标**：用户自然语言输入 → Agent 规划 → 调工具 → 检索/生成 → 校验 → 输出，全程可回放。

| 阶段 | 内容 | 状态 |
|------|------|------|
| **① 基础** | 修正路径、状态诊断、LangSmith 可选接入 | ✅ 当前 |
| **② 本地 Span** | 每次 /chat/stream 写 JSONL：retrieve / 路由 / 生成 / fallback / 耗时 | ✅ 当前 |
| **③ LangGraph 节点** | 为 `router→retrieve→draft→verifier→citer` 每节点打 Span | 待做 |
| **④ 工具调用** | 入库 Agent、未来 ReAct 的 `bind_tools` 记录入参/出参/耗时 | 待做 |
| **⑤ 可视化** | 管理端 Trace 详情页：时间线树、性能、按 trace_id 检索 | 待做 |
| **⑥ 模型思考** | 若 API 返回 `reasoning_content` / 思维链，单独 Span 存档 | 待做 |

**Span 统一结构（预留）**：
```
trace_id → session_id → spans[]
  每 span: type, name, input, output, latency_ms, status, parent_id, meta
  type 枚举: run | graph_node | tool_call | llm_call | retrieval | verifier
```

**双路径说明**：
- 同步 `/chat` 走 **LangGraph**，开 LangSmith 可自动上报节点级 trace
- 流式 `/chat/stream` 目前绕过 Graph，需 **手动埋点**（② 先做这条主路径）

**推荐栈**：本地 JSONL（可控、离线） + LangSmith（可选云端）+ 自研 Timeline UI
            """
        )

    st.subheader("环境变量示例（需重启 API）")
    st.code(
        "# LangSmith 云端\n"
        "LANGCHAIN_TRACING_V2=true\n"
        "LANGCHAIN_API_KEY=lsv2_...\n"
        "LANGCHAIN_PROJECT=enterprise-rag\n\n"
        "# 本地 JSONL（/chat/stream 写入）\n"
        "LOCAL_TRACE_ENABLED=true",
        language="ini",
    )


if __name__ == "__main__":
    main()
