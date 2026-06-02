"""
企业 RAG 控制台：数据入库、RAG 对话、模型配置入口。

API: cd enterprise_rag/src && python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8001
本页: python -m streamlit run frontend/streamlit_app.py --server.port 8501
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

_FRONT = Path(__file__).resolve().parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
from _bootstrap import load_streamlit_common  # noqa: E402

scom = load_streamlit_common(_FRONT)


def _ingest_success_message(data: dict[str, Any]) -> str:
    n = data.get("chunks_indexed", "?")
    src = data.get("source", "") or "（未命名来源）"
    return f"入库成功：已为知识库写入 **{n}** 个可检索片段，来源为「{src}」。接下来可在「RAG 对话」里提问。"


def _chat_error_hint(status: int, text: str) -> str:
    if status == 400 and "API Key" in text:
        return "需要配置大模型密钥：请打开「模型与密钥配置」保存 API Key。"
    if status in (401, 403):
        return "访问被拒绝，请联系管理员。"
    if status == 0 or not text:
        return text
    return text[:800]


def _run_with_backend(api_base: str, action_label: str, fn) -> None:
    """静默等待后端就绪后执行操作；失败时仅展示简短提示。"""
    with st.spinner(f"{action_label}中…"):
        if not scom._ensure_backend_silent(api_base):
            st.error(scom.SERVICE_UNAVAILABLE)
            return
        fn()


def main() -> None:
    st.set_page_config(
        page_title="企业知识库助手",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={"About": None},
    )
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    api_base = scom.get_api_base()

    st.title("企业知识库助手")
    st.caption("把文档放进知识库，用自然语言提问；无需编写代码。")
    st.page_link("pages/model_config.py", label="模型与密钥配置", icon="⚙️")

    with st.expander("首次使用？按这三步操作", expanded=False):
        st.markdown(
            """
1. **配置对话模型**：点击上方「模型与密钥配置」，填入厂商提供的地址与 **API Key** 并保存。  
2. **上传或粘贴文档入库**。  
3. 在「**RAG 对话**」里用日常用语提问即可。
            """
        )

    with st.sidebar:
        st.subheader("身份")
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
        if isinstance(prof_data, dict) and prof_data.get("_auth_error"):
            st.caption("模型列表需要网关密钥，请在环境变量中配置 STREAMLIT_RAG_API_SECRET。")
        choices = scom.profile_labels(prof_data)
        picked = st.selectbox(
            "选择已保存的模型接入",
            choices,
            format_func=lambda x: x[0],
            index=0,
            help="在「模型与密钥配置」页保存厂商与密钥后，在此选择。",
        )
        selected_profile_token = picked[1]

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
            dept_f = st.text_input("文档归属部门", value=user_department, key="dept_file")
            perm_f = st.text_input("可见范围标签", value="public", key="perm_file")
            if up and st.button("上传并入库", key="btn_upload"):
                def _upload() -> None:
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
                            st.error(f"入库失败：{_chat_error_hint(r.status_code, r.text)}")
                    except (httpx.TimeoutException, httpx.ConnectError):
                        st.error(scom.SERVICE_UNAVAILABLE)
                    except Exception as e:
                        st.error(f"入库失败：{e}")

                _run_with_backend(api_base, "文件入库", _upload)

        with col_b:
            st.subheader("粘贴文本")
            src = st.text_input("文档名称（便于以后查找来源）", value="paste.txt", key="paste_src")
            raw = st.text_area("原始内容", height=220, key="paste_raw")
            dept_t = st.text_input("文档归属部门", value=user_department, key="dept_text")
            perm_t = st.text_input("可见范围标签", value="public", key="perm_text")
            pc1, pc2 = st.columns(2)
            with pc1:
                if st.button("仅预览清洗", key="btn_preview") and raw.strip():
                    def _preview() -> None:
                        try:
                            with scom.http_client(api_base) as c:
                                r = c.post(
                                    "/ingest/preview",
                                    json={"text": raw, "use_presidio": use_presidio},
                                )
                            if r.status_code == 200:
                                st.text_area("清洗后", value=r.json().get("cleaned", ""), height=200)
                            else:
                                st.error(f"预览失败：{_chat_error_hint(r.status_code, r.text)}")
                        except (httpx.TimeoutException, httpx.ConnectError):
                            st.error(scom.SERVICE_UNAVAILABLE)
                        except Exception as e:
                            st.error(f"预览失败：{e}")

                    _run_with_backend(api_base, "预览", _preview)
            with pc2:
                if st.button("清洗并入库", key="btn_ingest_text") and raw.strip():
                    def _ingest_text() -> None:
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
                                st.error(f"入库失败：{_chat_error_hint(r.status_code, r.text)}")
                        except (httpx.TimeoutException, httpx.ConnectError):
                            st.error(scom.SERVICE_UNAVAILABLE)
                        except Exception as e:
                            st.error(f"入库失败：{e}")

                    _run_with_backend(api_base, "文本入库", _ingest_text)

    with tab_chat:
        st.markdown("根据已入库的文档回答问题。大模型密钥在「模型与密钥配置」中设置，此处不会显示。")

        with st.expander("高级参数（一般不用改）", expanded=False):
            chat_model_override = st.text_input("指定其它模型名（可选）", value="")
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
                        st.json(m["meta"])

        if prompt := st.chat_input("输入问题…"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                def _chat() -> None:
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
                                "source_refs": data.get("source_refs"),
                            }
                            with st.expander("参考了哪些内容（可选看）"):
                                st.json(meta)
                            st.session_state.messages.append(
                                {"role": "assistant", "content": ans, "meta": meta}
                            )
                        else:
                            hint = _chat_error_hint(r.status_code, r.text)
                            err = f"请求失败：{hint}"
                            st.error(err)
                            st.session_state.messages.append({"role": "assistant", "content": err})
                    except (httpx.TimeoutException, httpx.ConnectError):
                        st.error(scom.SERVICE_UNAVAILABLE)
                        st.session_state.messages.append({"role": "assistant", "content": scom.SERVICE_UNAVAILABLE})
                    except Exception as e:
                        st.error(str(e))
                        st.session_state.messages.append({"role": "assistant", "content": str(e)})

                with st.spinner("思考中…"):
                    if not scom._ensure_backend_silent(api_base):
                        st.error(scom.SERVICE_UNAVAILABLE)
                        st.session_state.messages.append({"role": "assistant", "content": scom.SERVICE_UNAVAILABLE})
                    else:
                        _chat()


if __name__ == "__main__":
    main()
