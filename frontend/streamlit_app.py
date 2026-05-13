"""
企业 RAG 控制台：数据入库、RAG 对话、模型配置入口。

API: cd enterprise_rag/src && python -m uvicorn api.main:app --reload --port 8001
本页: python -m streamlit run frontend/streamlit_app.py --server.port 8501
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

_FRONT = Path(__file__).resolve().parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
import streamlit_common as scom  # noqa: E402


def _get_public_config(base: str) -> dict[str, Any] | None:
    try:
        with scom.http_client(base, timeout=15.0) as c:
            r = c.get("/config/public")
            if r.status_code == 200:
                return r.json()
    except Exception:
        return None
    return None


def _ingest_success_message(data: dict[str, Any]) -> str:
    n = data.get("chunks_indexed", "?")
    src = data.get("source", "") or "（未命名来源）"
    return f"入库成功：已为知识库写入 **{n}** 个可检索片段，来源为「{src}」。接下来可在「RAG 对话」里提问。"


def _chat_error_hint(status: int, text: str) -> str:
    if status == 400 and "API Key" in text:
        return "需要配置大模型密钥：请打开「模型与密钥配置」保存 API Key，或在服务器 `.env` 中填写 OPENAI_API_KEY。"
    if status in (401, 403):
        return "访问被拒绝：请检查侧栏「网关访问密码」是否与服务器 RAG_API_SECRET 一致。"
    if status == 0 or not text:
        return text
    return text[:800]


def main() -> None:
    st.set_page_config(
        page_title="企业知识库助手",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={"About": None},
    )
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    st.title("企业知识库助手")
    st.caption("把文档放进知识库，用自然语言提问；无需编写代码。")
    st.page_link("pages/model_config.py", label="模型与密钥配置", icon="⚙️")

    with st.expander("首次使用？按这三步操作", expanded=False):
        st.markdown(
            """
1. **先启动后端服务**（需由技术人员或按说明文档在本机执行一次）：在 `enterprise_rag/src` 目录运行 Uvicorn，并保证本页侧栏里的「服务地址」能打开。  
2. **配置对话模型**：点击上方「模型与密钥配置」，填入厂商提供的地址与 **API Key** 并保存；回到本页在侧栏选择要用的接入方式。  
3. **上传或粘贴文档入库**，再在「RAG 对话」里用日常用语提问即可。
            """
        )

    with st.sidebar:
        st.subheader("连接与身份")
        api_base = st.text_input(
            "服务地址（后端 API）",
            key="rag_api_base",
            help="一般为 http://127.0.0.1:8001 ，与启动 Uvicorn 时填写的端口一致。",
        )
        st.text_input(
            "网关访问密码（可选）",
            type="password",
            key="rag_api_secret",
            help="仅当服务器开启了访问密码时填写；与 .env 中的 RAG_API_SECRET 一致。",
        )
        if st.button("测试与后端是否连通", key="btn_health"):
            try:
                with scom.http_client(api_base, timeout=10.0) as c:
                    r = c.get("/health")
                st.session_state["_health_ok"] = r.status_code == 200
                st.session_state["_health_detail"] = r.text[:500] if r.status_code != 200 else ""
            except Exception as e:
                st.session_state["_health_ok"] = False
                st.session_state["_health_detail"] = str(e)
        if "_health_ok" in st.session_state:
            if st.session_state["_health_ok"]:
                st.success("已连通，后端正常。")
            else:
                st.error(
                    "无法连接。请确认：① 后端已启动；② 上方服务地址与端口正确；③ 若设置了网关密码，密码填写正确。"
                )
                if st.session_state.get("_health_detail"):
                    st.caption(st.session_state["_health_detail"][:400])

        user_id = st.text_input("您的用户标识", value="demo_user", help="用于区分不同使用者，可随意填写英文或工号。")
        user_department = st.text_input("所属部门", value="general", help="与文档入库时填写的部门一致时，更易命中允许检索的范围。")
        allowed_raw = st.text_input(
            "仅检索指定文档（可选）",
            value="",
            help="高级用法：填写来源文件名，多个用英文逗号分隔；留空表示可检索库内全部已授权文档。",
        )
        st.divider()
        st.subheader("对话用哪家模型")
        prof_data = scom.fetch_model_profiles(api_base)
        choices = scom.profile_labels(prof_data)
        picked = st.selectbox(
            "选择已保存的模型接入",
            choices,
            format_func=lambda x: x[0],
            index=0,
            help="在「模型与密钥配置」页保存厂商与密钥后，在此选择；未配置时可选用「跟随服务端默认」。",
        )
        selected_profile_token = picked[1]

        st.divider()
        st.subheader("知识库侧模型（只读）")
        cfg = _get_public_config(api_base)
        if cfg:
            st.text(f"向量化模型: {cfg.get('embedding_model', '')}")
            st.text(f"重排模型: {cfg.get('reranker_model', '')}")
            st.text(f"服务器默认对话模型: {cfg.get('default_chat_model', '')}")
            st.caption("以上由服务器配置；更换向量化模型后通常需要重新入库。")
        else:
            st.warning("暂时读不到服务器配置，请检查服务地址或网络。")

    allowed_sources = (
        [s.strip() for s in allowed_raw.split(",") if s.strip()] if allowed_raw.strip() else None
    )

    force_env = selected_profile_token == "__env__"
    model_profile_id = None if selected_profile_token in ("", "__env__") else selected_profile_token

    tab_ingest, tab_chat = st.tabs(["数据入库", "RAG 对话"])

    with tab_ingest:
        st.markdown("支持 **上传文件** 或 **粘贴文字**。可先「仅预览清洗」确认内容再入库。")
        use_presidio = st.checkbox("对身份证号、电话等敏感信息做自动脱敏（推荐开启）", value=True, key="ingest_presidio")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("文件上传")
            up = st.file_uploader("选择文件", type=["txt", "md", "pdf", "docx", "html"])
            dept_f = st.text_input("文档归属部门", value=user_department, key="dept_file", help="与对话侧「所属部门」配合，用于权限与过滤。")
            perm_f = st.text_input("可见范围标签", value="public", key="perm_file", help="一般填 public；若系统按标签控权，请按管理员要求填写。")
            if up and st.button("上传并入库", key="btn_upload"):
                with st.spinner("入库中…"):
                    try:
                        files = {"file": (up.name, up.getvalue(), up.type or "application/octet-stream")}
                        params: dict[str, str] = {}
                        if dept_f.strip():
                            params["department"] = dept_f.strip()
                        if perm_f.strip():
                            params["permission_label"] = perm_f.strip()
                        with scom.http_client(api_base) as c:
                            r = c.post("/ingest/upload", files=files, params=params)
                        if r.status_code == 200:
                            st.success(_ingest_success_message(r.json()))
                        else:
                            st.error(f"入库失败（{r.status_code}）：{_chat_error_hint(r.status_code, r.text)}")
                    except Exception as e:
                        st.exception(e)

        with col_b:
            st.subheader("粘贴文本")
            src = st.text_input("文档名称（便于以后查找来源）", value="paste.txt", key="paste_src")
            raw = st.text_area("原始内容", height=220, key="paste_raw")
            dept_t = st.text_input("文档归属部门", value=user_department, key="dept_text")
            perm_t = st.text_input("可见范围标签", value="public", key="perm_text")
            pc1, pc2 = st.columns(2)
            with pc1:
                if st.button("仅预览清洗", key="btn_preview") and raw.strip():
                    try:
                        with scom.http_client(api_base) as c:
                            r = c.post(
                                "/ingest/preview",
                                json={"text": raw, "use_presidio": use_presidio},
                            )
                        if r.status_code == 200:
                            st.text_area("清洗后", value=r.json().get("cleaned", ""), height=200)
                        else:
                            st.error(f"{r.status_code}: {r.text}")
                    except Exception as e:
                        st.exception(e)
            with pc2:
                if st.button("清洗并入库", key="btn_ingest_text") and raw.strip():
                    with st.spinner("入库中…"):
                        try:
                            body = {
                                "text": raw,
                                "source": src.strip() or "paste.txt",
                                "department": dept_t.strip() or None,
                                "permission_label": perm_t.strip() or None,
                                "use_presidio": use_presidio,
                            }
                            with scom.http_client(api_base) as c:
                                r = c.post("/ingest/text", json=body)
                            if r.status_code == 200:
                                st.success(_ingest_success_message(r.json()))
                            else:
                                st.error(f"入库失败（{r.status_code}）：{_chat_error_hint(r.status_code, r.text)}")
                        except Exception as e:
                            st.exception(e)

    with tab_chat:
        st.markdown("根据已入库的文档回答问题。大模型密钥在「模型与密钥配置」中设置，此处不会显示。")

        with st.expander("高级参数（一般不用改）", expanded=False):
            chat_model_override = st.text_input("指定其它模型名（可选）", value="", help="留空则使用所选接入里保存的默认模型。")
            temperature = st.slider("生成温度", 0.0, 2.0, 0.2, 0.05)
            verifier_temperature = st.slider("校验温度", 0.0, 1.0, 0.0, 0.05)
            max_rw = st.number_input("改写 max_tokens", min_value=32, max_value=4096, value=128, step=8)
            max_ans = st.number_input("回答 max_tokens（0=不限制）", min_value=0, max_value=128000, value=0, step=256)
            max_ver = st.number_input("校验 max_tokens（0=默认8）", min_value=0, max_value=2048, value=0, step=1)

        if "messages" not in st.session_state:
            st.session_state.messages = []

        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m["role"] == "assistant" and m.get("meta"):
                    with st.expander("参考了哪些内容（可选看）"):
                        st.caption("以下为系统检索时使用的改写问句与参考片段标识。")
                        st.json(m["meta"])

        if prompt := st.chat_input("输入问题…"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                with st.spinner("思考中…"):
                    try:
                        payload: dict[str, Any] = {
                            "message": prompt,
                            "user_id": user_id,
                            "user_department": user_department,
                            "allowed_sources": allowed_sources,
                            "model_profile_id": model_profile_id,
                            "force_env_llm": force_env,
                            "temperature": temperature,
                            "verifier_temperature": verifier_temperature,
                            "max_tokens_rewrite": int(max_rw),
                        }
                        cm = chat_model_override.strip()
                        if cm:
                            payload["chat_model"] = cm
                        if max_ans > 0:
                            payload["max_tokens_answer"] = int(max_ans)
                        if max_ver > 0:
                            payload["max_tokens_verifier"] = int(max_ver)

                        with scom.http_client(api_base) as c:
                            r = c.post("/chat", json=payload)
                        if r.status_code == 200:
                            data = r.json()
                            ans = data.get("answer") or ""
                            st.markdown(ans)
                            meta = {
                                "rewritten_query": data.get("rewritten_query"),
                                "sources": data.get("sources"),
                            }
                            with st.expander("参考了哪些内容（可选看）"):
                                st.caption("以下为系统检索时使用的改写问句与参考片段标识。")
                                st.json(meta)
                            st.session_state.messages.append(
                                {"role": "assistant", "content": ans, "meta": meta}
                            )
                        else:
                            hint = _chat_error_hint(r.status_code, r.text)
                            err = f"请求失败（{r.status_code}）：{hint}"
                            st.error(err)
                            st.session_state.messages.append({"role": "assistant", "content": err})
                    except Exception as e:
                        st.exception(e)
                        st.session_state.messages.append({"role": "assistant", "content": str(e)})


if __name__ == "__main__":
    main()
