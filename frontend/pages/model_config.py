"""
模型接入配置（多厂商 OpenAI 兼容）。密钥保存在服务端 data/model_profiles.json，列表接口不返回明文。
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_FRONT = Path(__file__).resolve().parent.parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
import streamlit_common as scom  # noqa: E402


def main() -> None:
    st.set_page_config(page_title="模型与密钥配置", layout="wide", menu_items={"About": None})
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    st.title("模型与密钥配置")
    st.caption("把大模型服务的网址和密钥保存在本系统内，供「企业知识库助手」对话使用；密钥不会完整显示给其他人。")
    st.page_link("streamlit_app.py", label="返回知识库助手", icon="🏠")

    api_base = st.text_input("服务地址（后端 API）", key="rag_api_base", help="与主控制台侧栏一致，例如 http://127.0.0.1:8001")

    with st.expander("各厂商地址怎么填？（点击展开）", expanded=False):
        st.markdown(
            """
            - **DeepSeek**：`api_base` 填 `https://api.deepseek.com`，路径留空（会自动拼 `/v1`），模型如 `deepseek-chat`。
            - **通义千问 OpenAI 兼容**：`api_base` 填 `https://dashscope.aliyuncs.com`，`api_path` 填 `/compatible-mode/v1`，模型如 `qwen-plus`。
            - **OpenAI**：`https://api.openai.com`，路径留空。
            - 其它兼容 **OpenAI Chat Completions** 的网关同理填写 Base URL；路径仅在厂商要求时填写。
            """
        )

    st.subheader("新建或更新一条配置")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("显示名称", placeholder="例如：公司用的通义千问")
        vendor_choice = st.selectbox(
            "厂商",
            [
                "custom",
                "deepseek",
                "qwen",
                "openai",
                "moonshot",
                "zhipu",
            ],
            format_func=lambda x: {
                "custom": "自定义 / 其它",
                "deepseek": "DeepSeek",
                "qwen": "阿里云通义千问",
                "openai": "OpenAI",
                "moonshot": "Moonshot(Kimi)",
                "zhipu": "智谱 GLM",
            }.get(x, x),
        )
        api_base_url = st.text_input("服务网址（Base）", placeholder="https://api.deepseek.com")
        api_path = st.text_input("路径后缀（多数情况可留空）", placeholder="通义千问兼容模式填 /compatible-mode/v1")
    with col2:
        default_model = st.text_input("模型名称", placeholder="如 deepseek-chat、qwen-plus")
        api_key = st.text_input("API Key（密钥）", type="password", help="保存后不会在列表里完整显示。")
        edit_id = st.text_input(
            "若要修改已有配置，填写其配置编号（新建请留空）",
            value="",
            help="在下方列表每条卡片里可看到「配置编号」；普通用户一般由管理员代为填写。",
        )

    if st.button("保存到服务器", type="primary"):
        if not name.strip() or not api_base_url.strip() or not default_model.strip():
            st.error("请填写显示名称、服务网址和模型名称。")
        else:
            body = {
                "name": name.strip(),
                "vendor": vendor_choice,
                "api_base": api_base_url.strip(),
                "api_path": api_path.strip() or None,
                "default_model": default_model.strip(),
                "api_key": api_key,
            }
            try:
                with scom.http_client(api_base) as c:
                    if edit_id.strip():
                        r = c.put(f"/config/model-profiles/{edit_id.strip()}", json=body)
                    else:
                        r = c.post("/config/model-profiles", json=body)
                if r.status_code == 200:
                    st.success("已保存。请回到「企业知识库助手」，在侧栏选择刚保存的接入方式。")
                    with st.expander("技术详情（可选）"):
                        st.json(r.json())
                else:
                    st.error(f"{r.status_code}: {r.text}")
            except Exception as e:
                st.exception(e)

    st.divider()
    st.subheader("已保存的配置")
    try:
        with scom.http_client(api_base, timeout=20.0) as c:
            r = c.get("/config/model-profiles")
        if r.status_code != 200:
            st.error(f"加载失败 {r.status_code}: {r.text}")
            return
        data = r.json()
        profiles = data.get("profiles") or []
        default_id = data.get("default_profile_id")
        if not profiles:
            st.info("暂无配置，请在上方新建。")
        for p in profiles:
            pid = p.get("id", "")
            with st.container(border=True):
                st.write(f"**{p.get('name')}** · `{p.get('vendor')}` · 模型 `{p.get('default_model')}`")
                st.caption(f"配置编号（更新时需要）：`{pid}`")
                st.text(f"Base: {p.get('combined_base') or p.get('api_base')}")
                st.caption(f"密钥: {'已配置 ' + p.get('api_key_hint', '') if p.get('has_api_key') else '未配置'}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("设为默认", key=f"def_{pid}"):
                        with scom.http_client(api_base) as c:
                            rr = c.post(f"/config/model-profiles/{pid}/default")
                        if rr.status_code == 200:
                            st.success("已设为默认")
                        else:
                            st.error(rr.text)
                with c2:
                    if st.button("删除", key=f"del_{pid}"):
                        with scom.http_client(api_base) as c:
                            rr = c.delete(f"/config/model-profiles/{pid}")
                        if rr.status_code == 200:
                            st.success("已删除")
                        else:
                            st.error(rr.text)
                with c3:
                    if str(pid) == str(default_id or ""):
                        st.caption("当前为默认")
    except Exception as e:
        st.exception(e)


if __name__ == "__main__":
    main()
