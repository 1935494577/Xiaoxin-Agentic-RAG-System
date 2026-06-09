"""
模型接入配置（多厂商 OpenAI 兼容）。密钥保存在服务端 data/model_profiles.json，列表接口不返回明文。
"""

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
from page_init import init_app_page, invalidate_page_cache  # noqa: E402

scom = load_streamlit_common(_FRONT)

VENDOR_OPTIONS = ["custom", "deepseek", "qwen", "openai", "moonshot", "zhipu"]
VENDOR_LABELS = {
    "custom": "自定义 / 其它",
    "deepseek": "DeepSeek",
    "qwen": "阿里云通义千问",
    "openai": "OpenAI",
    "moonshot": "Moonshot(Kimi)",
    "zhipu": "智谱 GLM",
}


def _init_form_state() -> None:
    defaults = {
        "mc_editing_id": "",
        "mc_name": "",
        "mc_vendor": "custom",
        "mc_api_base": "",
        "mc_api_path": "",
        "mc_default_model": "",
        "mc_api_key": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def _load_profile_into_form(profile: dict[str, Any]) -> None:
    st.session_state["mc_editing_id"] = str(profile.get("id") or "")
    st.session_state["mc_name"] = str(profile.get("name") or "")
    vendor = str(profile.get("vendor") or "custom")
    st.session_state["mc_vendor"] = vendor if vendor in VENDOR_OPTIONS else "custom"
    st.session_state["mc_api_base"] = str(profile.get("api_base") or "")
    st.session_state["mc_api_path"] = str(profile.get("api_path") or "")
    st.session_state["mc_default_model"] = str(profile.get("default_model") or "")
    st.session_state["mc_api_key"] = ""


def _clear_form() -> None:
    st.session_state["mc_editing_id"] = ""
    st.session_state["mc_name"] = ""
    st.session_state["mc_vendor"] = "custom"
    st.session_state["mc_api_base"] = ""
    st.session_state["mc_api_path"] = ""
    st.session_state["mc_default_model"] = ""
    st.session_state["mc_api_key"] = ""


def _build_save_body() -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": st.session_state["mc_name"].strip(),
        "vendor": st.session_state["mc_vendor"],
        "api_base": st.session_state["mc_api_base"].strip(),
        "api_path": st.session_state["mc_api_path"].strip() or None,
        "default_model": st.session_state["mc_default_model"].strip(),
    }
    key = st.session_state["mc_api_key"].strip()
    if key:
        body["api_key"] = key
    return body


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API
    _init_form_state()

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    prof_data = scom.fetch_model_profiles(api_base)
    ui, _, _ = init_app_page(api_base, auth, prof_data, check_model_status=True, nav_id="models")

    st.title("模型设置")
    st.caption("配置大模型接入；保存前可用「测试连接」验证，右上角状态灯绿/红表示当前默认模型是否连通。")

    with st.expander("各厂商地址怎么填？（点击展开）", expanded=False):
        st.markdown(
            """
            - **DeepSeek**：`api_base` 填 `https://api.deepseek.com`，路径留空（会自动拼 `/v1`），模型如 `deepseek-chat`。
            - **通义千问 OpenAI 兼容**：`api_base` 填 `https://dashscope.aliyuncs.com`，`api_path` 填 `/compatible-mode/v1`，模型如 `qwen-plus`。
            - **OpenAI**：`https://api.openai.com`，路径留空。
            - 其它兼容 **OpenAI Chat Completions** 的网关同理填写 Base URL；路径仅在厂商要求时填写。
            """
        )

    editing_id = st.session_state["mc_editing_id"].strip()
    if editing_id:
        st.info(f"正在编辑配置 `{editing_id}`。留空「API Key」则保留原密钥；点「取消编辑」可新建。")
    else:
        st.subheader("新建配置")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("显示名称", key="mc_name", placeholder="例如：公司用的通义千问")
        st.selectbox(
            "厂商",
            VENDOR_OPTIONS,
            key="mc_vendor",
            format_func=lambda x: VENDOR_LABELS.get(x, x),
        )
        st.text_input("服务网址（Base）", key="mc_api_base", placeholder="https://api.deepseek.com")
        st.text_input("路径后缀（多数情况可留空）", key="mc_api_path", placeholder="通义千问兼容模式填 /compatible-mode/v1")
    with col2:
        st.text_input("模型名称", key="mc_default_model", placeholder="如 deepseek-chat、qwen-plus")
        st.text_input(
            "API Key（密钥）",
            key="mc_api_key",
            type="password",
            help="编辑已有配置时留空表示不修改原密钥。",
        )

    btn_save, btn_cancel, btn_test = st.columns([1, 1, 1])
    with btn_save:
        save_clicked = st.button("保存到服务器", type="primary")
    with btn_cancel:
        if editing_id and st.button("取消编辑"):
            _clear_form()
            st.rerun()
    with btn_test:
        test_clicked = st.button("测试连接")

    if test_clicked:
        if not st.session_state["mc_api_base"].strip() or not st.session_state["mc_default_model"].strip():
            st.error("请填写服务网址和模型名称后再测试。")
        elif not editing_id and not st.session_state["mc_api_key"].strip():
            st.error("新建配置时请填写 API Key 后再测试。")
        else:
            body = _build_save_body()
            if not body.get("api_key") and editing_id:
                try:
                    with scom.http_client(api_base) as c:
                        r = c.post(f"/config/model-profiles/{editing_id.strip()}/test")
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("connected"):
                            st.success(f"连接成功：{data.get('message', '')}")
                        else:
                            st.error(f"连接失败：{data.get('message', '')}")
                    else:
                        st.error(r.text[:500])
                except (httpx.ConnectError, httpx.TimeoutException):
                    st.error(scom.SERVICE_UNAVAILABLE)
            else:
                if not body.get("api_key"):
                    st.error("请填写 API Key 后再测试。")
                else:
                    try:
                        with scom.http_client(api_base) as c:
                            r = c.post("/config/model-profiles/test", json=body)
                        if r.status_code == 200:
                            data = r.json()
                            if data.get("connected"):
                                st.success(f"连接成功：{data.get('message', '')}")
                            else:
                                st.error(f"连接失败：{data.get('message', '')}")
                        else:
                            st.error(r.text[:500])
                    except (httpx.ConnectError, httpx.TimeoutException):
                        st.error(scom.SERVICE_UNAVAILABLE)

    if save_clicked:
        if not st.session_state["mc_name"].strip() or not st.session_state["mc_api_base"].strip():
            st.error("请填写显示名称和服务网址。")
        elif not st.session_state["mc_default_model"].strip():
            st.error("请填写模型名称。")
        elif not editing_id and not st.session_state["mc_api_key"].strip():
            st.error("新建配置时请填写 API Key。")
        else:
            body = _build_save_body()
            try:
                with scom.http_client(api_base) as c:
                    if editing_id:
                        r = c.put(f"/config/model-profiles/{editing_id}", json=body)
                    else:
                        r = c.post("/config/model-profiles", json=body)
                if r.status_code == 200:
                    saved = r.json()
                    invalidate_page_cache()
                    st.success(
                        f"已{'更新' if editing_id else '保存'}「{saved.get('name', '')}」。"
                        "请回到「企业知识库助手」，在侧栏选择该接入方式。"
                    )
                    _clear_form()
                    st.rerun()
                else:
                    st.error(f"{r.status_code}: {r.text}")
            except (httpx.ConnectError, httpx.TimeoutException):
                st.error(scom.SERVICE_UNAVAILABLE)
            except Exception as e:
                st.error(f"保存失败：{e}")

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
            pid = str(p.get("id", ""))
            is_editing = pid == editing_id
            with st.container(border=True):
                title = f"**{p.get('name')}** · `{p.get('vendor')}` · 模型 `{p.get('default_model')}`"
                if is_editing:
                    title += " · **（编辑中）**"
                st.write(title)
                st.caption(f"配置编号：`{pid}`")
                st.text(f"Base: {p.get('combined_base') or p.get('api_base')}")
                st.caption(f"密钥: {'已配置 ' + p.get('api_key_hint', '') if p.get('has_api_key') else '未配置'}")
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    if st.button("编辑", key=f"edit_{pid}", disabled=is_editing):
                        _load_profile_into_form(p)
                        st.rerun()
                with c2:
                    if st.button("测试", key=f"test_{pid}"):
                        with scom.http_client(api_base) as c:
                            rr = c.post(f"/config/model-profiles/{pid}/test")
                        if rr.status_code == 200:
                            data = rr.json()
                            if data.get("connected"):
                                st.success("连接成功")
                            else:
                                st.error(data.get("message", "连接失败"))
                        else:
                            st.error(rr.text[:200])
                with c3:
                    if st.button("设为默认", key=f"def_{pid}"):
                        with scom.http_client(api_base) as c:
                            rr = c.post(f"/config/model-profiles/{pid}/default")
                        if rr.status_code == 200:
                            st.success("已设为默认")
                            st.rerun()
                        else:
                            st.error(rr.text)
                with c4:
                    if st.button("删除", key=f"del_{pid}"):
                        with scom.http_client(api_base) as c:
                            rr = c.delete(f"/config/model-profiles/{pid}")
                        if rr.status_code == 200:
                            if editing_id == pid:
                                _clear_form()
                            st.success("已删除")
                            st.rerun()
                        else:
                            st.error(rr.text)
                with c5:
                    if str(pid) == str(default_id or ""):
                        st.caption("★ 当前默认")
    except (httpx.ConnectError, httpx.TimeoutException):
        st.error(scom.SERVICE_UNAVAILABLE)
    except Exception as e:
        st.error(f"加载失败：{e}")


if __name__ == "__main__":
    main()
