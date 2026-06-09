"""外观与 Logo 配置（同步服务端 ui_config.json）。"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import streamlit as st

_FRONT = Path(__file__).resolve().parent.parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
from _bootstrap import load_streamlit_common  # noqa: E402
from ui_theme import fetch_ui_config, render_minimal_sidebar  # noqa: E402

scom = load_streamlit_common(_FRONT)


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    ui = fetch_ui_config(api_base, auth)

    render_minimal_sidebar(ui, api_base, auth)

    st.title("外观配置")
    st.caption("配置左上角 Logo 文案、应用标题与 RAG 对话推荐问题；保存后全站同步。")

    with st.form("brand_form"):
        logo_en = st.text_input("Logo 英文", value=str(ui.get("logo_en") or "JNAO"))
        logo_cn = st.text_input("Logo 中文", value=str(ui.get("logo_cn") or "劲脑"))
        app_title = st.text_input("应用标题", value=str(ui.get("app_title") or ""))
        app_tagline = st.text_area("副标题", value=str(ui.get("app_tagline") or ""), height=80)
        questions_raw = st.text_area(
            "RAG 推荐问题（每行一条，最多 12 条）",
            value="\n".join(ui.get("suggested_questions") or []),
            height=120,
        )
        clear_logo = st.checkbox("清除已上传的 Logo 图片（仅保留文字 Logo）")
        submitted = st.form_submit_button("保存外观配置", type="primary")

    logo_file = st.file_uploader("上传 Logo 图片（PNG/JPG，可选，最大 2MB）", type=["png", "jpg", "jpeg", "webp", "svg"])

    if submitted:
        body = {
            "logo_en": logo_en.strip(),
            "logo_cn": logo_cn.strip(),
            "app_title": app_title.strip(),
            "app_tagline": app_tagline.strip(),
            "suggested_questions": [ln.strip() for ln in questions_raw.splitlines() if ln.strip()],
            "clear_logo_image": clear_logo,
        }
        try:
            with scom.http_client(api_base) as c:
                r = c.put("/config/ui", json=body)
            if r.status_code != 200:
                st.error(f"保存失败：{r.status_code} {r.text}")
            else:
                if logo_file is not None:
                    files = {"file": (logo_file.name, logo_file.getvalue(), logo_file.type or "image/png")}
                    with scom.http_client(api_base) as c:
                        lr = c.post("/config/ui/logo", files=files)
                    if lr.status_code != 200:
                        st.warning(f"文字配置已保存，但 Logo 图片上传失败：{lr.text}")
                    else:
                        st.success("外观与 Logo 已保存。")
                        st.rerun()
                else:
                    st.success("外观配置已保存。")
                    st.rerun()
        except (httpx.ConnectError, httpx.TimeoutException):
            st.error(scom.SERVICE_UNAVAILABLE)
        except Exception as e:
            st.error(str(e))
    elif logo_file is not None and st.button("仅上传 Logo 图片"):
        try:
            files = {"file": (logo_file.name, logo_file.getvalue(), logo_file.type or "image/png")}
            with scom.http_client(api_base) as c:
                r = c.post("/config/ui/logo", files=files)
            if r.status_code == 200:
                st.success("Logo 图片已上传。")
                st.rerun()
            else:
                st.error(r.text)
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.subheader("预览")
    if ui.get("has_logo_image"):
        try:
            with scom.http_client(api_base) as c:
                img = c.get("/config/ui/logo")
            if img.status_code == 200:
                st.image(img.content, caption="当前 Logo 图片")
        except Exception:
            pass
    st.markdown(
        f'<span style="color:#e53935;font-weight:800;font-size:1.4rem">{ui.get("logo_en", "JNAO")}</span>'
        f' <span style="font-weight:800;font-size:1.4rem">{ui.get("logo_cn", "劲脑")}</span>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
