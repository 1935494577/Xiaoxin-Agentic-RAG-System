"""数据入库 — 已清洗 / 未清洗 选项卡。"""

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
from ui_theme import render_page_header  # noqa: E402
from user_profile import get_dept_code, init_user_profile_state  # noqa: E402

scom = load_streamlit_common(_FRONT)


def _parse_custom_tags(raw: str) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    return [t.strip() for t in str(raw).replace("，", ",").split(",") if t.strip()]


def _selected_ingest_tags(ui: dict[str, Any]) -> list[str]:
    presets = ui.get("ingest_tag_presets") or []
    picked = st.session_state.get("ingest_tags_selected") or []
    custom = _parse_custom_tags(st.session_state.get("ingest_tags_custom") or "")
    out: list[str] = []
    seen: set[str] = set()
    for item in list(picked) + custom:
        t = str(item).strip()
        if not t:
            continue
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def _ingest_result_message(data: dict[str, Any]) -> str:
    n = data.get("chunks_indexed", 0)
    src = Path(str(data.get("source") or "文档")).name
    mode = data.get("ingest_mode") or "pre_cleaned"
    if mode in ("pre_cleaned", "raw"):
        mode_label = "已清洗"
    else:
        mode_label = "未清洗"
    tools = data.get("tools_used") or []
    tool_hint = f"（工具：{' → '.join(tools)}）" if tools else ""
    tags = data.get("tags") or []
    tag_hint = f"，标签：{'、'.join(tags)}" if tags else ""
    if n == 0:
        return data.get("message") or f"「{src}」已处理但未生成可检索片段，请检查文件内容。"
    return f"「{src}」{mode_label}入库成功，写入 {n} 个片段{tag_hint}{tool_hint}。可在「RAG 对话」中提问。"


def _upload(api_base: str, up, *, ingest_mode: str, tags: list[str]) -> None:
    if not scom.ping_health_fast(api_base):
        st.error(scom.SERVICE_UNAVAILABLE)
        return
    try:
        files = {"file": (up.name, up.getvalue(), up.type or "application/octet-stream")}
        params: dict[str, str | bool] = {
            "department": get_dept_code(),
            "permission_label": st.session_state.get("ingest_perm", "1"),
            "ingest_mode": ingest_mode,
        }
        if tags:
            params["tags"] = ",".join(tags)
        with scom.http_client(api_base) as c:
            r = c.post("/ingest/upload", files=files, params=params)
        if r.status_code == 200:
            st.success(_ingest_result_message(r.json()))
        elif r.status_code == 422:
            st.warning(r.json().get("detail", "文件处理失败"))
        else:
            st.error("入库失败，请稍后重试。")
    except (httpx.TimeoutException, httpx.ConnectError):
        st.error(scom.SERVICE_UNAVAILABLE)
    except Exception:
        st.error("入库失败，请稍后重试。")


def _render_tag_picker(ui: dict[str, Any]) -> None:
    presets = [str(x).strip() for x in (ui.get("ingest_tag_presets") or []) if str(x).strip()]
    st.markdown("**入库标签（可选）**")
    st.caption("为本次上传的文档打上标签，便于后续区分来源与类型；不选则与往常一样全库检索。")
    if presets:
        st.multiselect(
            "常用标签",
            options=presets,
            default=st.session_state.get("ingest_tags_selected") or [],
            key="ingest_tags_selected",
            placeholder="选择预设标签",
        )
    st.text_input(
        "自定义标签（逗号分隔）",
        key="ingest_tags_custom",
        placeholder="例如：2024春季, 销售手册",
    )
    selected = _selected_ingest_tags(ui)
    if selected:
        st.caption(f"将写入标签：{'、'.join(selected)}")


def _ingest_tab(api_base: str, ui: dict[str, Any], *, mode: str, key_prefix: str) -> None:
    exts = ui.get("supported_upload_extensions") or ["txt", "md", "pdf", "docx", "html"]
    fmt_slash = " / ".join(x.upper() for x in exts)
    desc = (
        "数据已完成清洗，仅解析并入库，不再执行脱敏、去水印等步骤。"
        if mode == "pre_cleaned"
        else "原始未处理数据，将自动调用清洗工具链（解析 → 规范化 → 去水印 → 脱敏）后入库。"
    )
    st.caption(desc)
    up = st.file_uploader(
        f"选择 {fmt_slash} 文件",
        type=list(exts),
        key=f"{key_prefix}_upload",
    )
    if up is not None:
        st.caption(f"已选择：{up.name}")
        if st.button("确认入库", type="primary", key=f"{key_prefix}_btn"):
            _upload(api_base, up, ingest_mode=mode, tags=_selected_ingest_tags(ui))


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API
    init_user_profile_state()
    if "ingest_perm" not in st.session_state:
        st.session_state.ingest_perm = "1"

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    prof_data = scom.fetch_model_profiles(api_base)
    ui, _, _ = init_app_page(api_base, auth, prof_data, check_model_status=False, nav_id="ingest")
    render_page_header(ui, compact=True)

    st.markdown('<div class="ingest-panel">', unsafe_allow_html=True)
    _render_tag_picker(ui)
    tab_pre, tab_unclean = st.tabs(["已清洗数据", "未清洗数据"])
    with tab_pre:
        _ingest_tab(api_base, ui, mode="pre_cleaned", key_prefix="pre")
    with tab_unclean:
        _ingest_tab(api_base, ui, mode="uncleaned", key_prefix="unclean")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
