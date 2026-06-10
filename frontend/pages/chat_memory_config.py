"""对话记忆与流式模式 — UI 侧配置。"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_FRONT = Path(__file__).resolve().parent.parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
from _bootstrap import load_streamlit_common  # noqa: E402
from page_init import init_app_page, invalidate_page_cache  # noqa: E402

scom = load_streamlit_common(_FRONT)


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    prof_data = scom.fetch_model_profiles(api_base)
    ui, _, _ = init_app_page(api_base, auth, prof_data, check_model_status=False, nav_id="memory")

    st.title("对话记忆")
    st.caption(
        "性能默认：8502 快速流式 + 路由 LLM 判断；同步 Verifier / 流式 fallback 默认关闭。"
        " 修改后需保存；8502 刷新生效，API 配置即时读取。"
    )

    c1, c2 = st.columns(2)
    with c1:
        max_turns = st.number_input(
            "短期记忆轮数（max_history_turns）",
            min_value=1,
            max_value=50,
            value=int(ui.get("max_history_turns") or 6),
            help="注入模型的最近对话轮数（每轮含用户+助手）。",
        )
        max_chars = st.number_input(
            "短期记忆字符上限（max_history_chars）",
            min_value=500,
            max_value=50000,
            value=int(ui.get("max_history_chars") or 6000),
            step=500,
        )
        kb_score = st.slider(
            "混合检索阈值（kb_min_score，无 LLM 判断时）",
            min_value=0.0,
            max_value=1.0,
            value=float(ui.get("kb_min_score") or 0.55),
            step=0.05,
            help="快速流式无重排时默认走 LLM 判断；关闭 LLM 判断后此项生效。",
        )
        rerank_score = st.number_input(
            "重排分阈值（kb_min_rerank_score）",
            min_value=-10.0,
            max_value=10.0,
            value=float(ui.get("kb_min_rerank_score") or 0.0),
            step=0.1,
            help="标准模式有重排分：低于此值视为与问题不相关，走通用回答。",
        )
    with c2:
        fast = st.toggle(
            "快速流式（stream_fast_mode，8502 默认）",
            value=bool(ui.get("stream_fast_mode", True)),
            help="跳过重排、减小 top_k，retrieve 通常更快。",
        )
        long_term = st.toggle(
            "长期记忆（long_term_memory_enabled）",
            value=bool(ui.get("long_term_memory_enabled", True)),
            help="开启后，请求带 session_id 时自动从 SQLite 加载历史。",
        )
        general_fb = st.toggle(
            "检索不足时走通用（general_fallback_enabled）",
            value=bool(ui.get("general_fallback_enabled", True)),
            help="路由阶段：判断资料不足则直接用通用回答。",
        )
        llm_judge = st.toggle(
            "LLM 相关性判断（kb_llm_judge）",
            value=bool(ui.get("kb_llm_judge", True)),
            help="无重排时必用；避免弱相关片段误走知识库。",
        )
        post_fb = st.toggle(
            "流式 KB 后再 fallback（kb_post_stream_fallback）",
            value=bool(ui.get("kb_post_stream_fallback", False)),
            help="默认关：避免 draft 后再打一次通用 LLM。",
        )
        stream_ver = st.toggle(
            "流式 Verifier（stream_verifier_enabled）",
            value=bool(ui.get("stream_verifier_enabled", False)),
        )
        graph_ver = st.toggle(
            "同步 /chat Verifier（graph_verifier_enabled）",
            value=bool(ui.get("graph_verifier_enabled", False)),
            help="LangGraph 校验节点，约 +1s；评测时可开。",
        )

    if st.button("保存", type="primary"):
        patch = {
            "stream_fast_mode": fast,
            "max_history_turns": int(max_turns),
            "max_history_chars": int(max_chars),
            "kb_min_score": float(kb_score),
            "kb_min_rerank_score": float(rerank_score),
            "kb_llm_judge": llm_judge,
            "long_term_memory_enabled": long_term,
            "general_fallback_enabled": general_fb,
            "kb_post_stream_fallback": post_fb,
            "stream_verifier_enabled": stream_ver,
            "graph_verifier_enabled": graph_ver,
        }
        try:
            with scom.http_client(api_base, timeout=15.0) as c:
                r = c.put("/config/ui", json=patch, headers=auth)
            if r.status_code == 200:
                invalidate_page_cache()
                st.success("已保存")
            else:
                st.error(r.text[:300])
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.markdown(
        "对话界面在 **Chat SPA（8502）**。"
        " 发送时传 `session_id` 或 `history` 即可启用多轮记忆。"
    )


if __name__ == "__main__":
    main()
