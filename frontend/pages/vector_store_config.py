"""向量库选择与切换 — 避免嵌入模型变更导致维度不匹配。"""

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


def _fetch_stores(api_base: str) -> tuple[dict[str, Any] | None, str]:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.get("/config/vector-stores")
            if r.status_code == 200:
                return r.json(), ""
            if r.status_code == 404:
                return None, (
                    f"API 已连接（{api_base}），但未找到向量库接口。"
                    "请**重启后端 API** 以加载最新代码：`powershell .\\scripts\\run-api.ps1`"
                )
            return None, f"API 返回 {r.status_code}：{r.text[:200]}"
    except httpx.ConnectError:
        return None, f"无法连接 API（{api_base}）。请确认后端已启动：`powershell .\\scripts\\run-api.ps1`"
    except httpx.TimeoutException:
        return None, f"连接 API 超时（{api_base}）。"
    except Exception as e:
        return None, str(e)
    return None, "未知错误"


def _activate(api_base: str, store_id: str) -> bool:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.put(f"/config/vector-stores/{store_id}/activate")
            return r.status_code == 200
    except Exception:
        return False


def _create(api_base: str, name: str, backend: str) -> bool:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.post("/config/vector-stores", json={"name": name, "backend": backend})
            return r.status_code == 200
    except Exception:
        return False


def _delete(api_base: str, store_id: str) -> tuple[bool, str]:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.delete(f"/config/vector-stores/{store_id}")
            if r.status_code == 200:
                return True, ""
            return False, r.json().get("detail", r.text[:200])
    except Exception as e:
        return False, str(e)


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    prof_data = scom.fetch_model_profiles(api_base)
    init_app_page(api_base, auth, prof_data, check_model_status=False)

    st.title("向量库设置")
    st.caption(
        "切换或新建向量库，使索引维度与当前嵌入模型一致。"
        "更换嵌入模型后建议新建向量库并重新入库，避免检索报错。"
    )
    st.caption(f"API 地址：`{api_base}`")

    data, err = _fetch_stores(api_base)
    if not data:
        st.error(err or "无法加载向量库配置，请确认 API 已启动。")
        return

    active = data.get("active") or {}
    if active:
        ok = active.get("compatible", True)
        st.info(
            f"**当前使用：** {active.get('name')} · {active.get('backend_label')} · "
            f"{active.get('vector_count', 0)} 条向量 · "
            f"索引 {active.get('embedding_dim') or '—'} 维 / "
            f"模型 {active.get('current_embedding_dim') or '—'} 维"
            + (" · ✅ 兼容" if ok else " · ⚠️ 维度不匹配，请新建库并重新入库")
        )

    st.subheader("已有向量库")
    stores = data.get("stores") or []
    if not stores:
        st.warning("暂无向量库，请下方新建。")
    for row in stores:
        sid = str(row.get("id") or "")
        cols = st.columns([4, 2, 2, 1, 1])
        with cols[0]:
            tag = "（当前）" if row.get("active") else ""
            compat = "✅" if row.get("compatible") else "⚠️"
            st.markdown(
                f"**{row.get('name')}** {tag} {compat}\n\n"
                f"{row.get('backend_label')} · 模型 {row.get('embedding_model')} · "
                f"{row.get('vector_count', 0)} 向量 / {row.get('bm25_docs', 0)} BM25"
            )
        with cols[1]:
            st.caption(f"索引维度：{row.get('embedding_dim') or '—'}")
        with cols[2]:
            st.caption(f"当前模型：{row.get('current_embedding_dim') or '—'} 维")
        with cols[3]:
            if not row.get("active"):
                if st.button("切换", key=f"act_{sid}"):
                    if _activate(api_base, sid):
                        st.success("已切换")
                        st.rerun()
                    else:
                        st.error("切换失败")
        with cols[4]:
            if not row.get("active"):
                if st.button("删除", key=f"del_{sid}"):
                    ok, msg = _delete(api_base, sid)
                    if ok:
                        st.rerun()
                    else:
                        st.warning(msg or "删除失败")

    st.subheader("新建向量库")
    backends = data.get("available_backends") or []
    backend_opts = [b for b in backends if b.get("available")]
    if not backend_opts:
        backend_opts = [{"id": "numpy", "label": "NumPy 文件"}]
    cur_model = (active or {}).get("current_embedding_model") or "当前嵌入模型"
    cur_dim = (active or {}).get("current_embedding_dim") or "?"
    default_name = f"{cur_model.split('/')[-1]}-{cur_dim}维"
    name = st.text_input("名称", value=default_name, max_chars=64)
    backend = st.selectbox(
        "存储类型",
        options=[b["id"] for b in backend_opts],
        format_func=lambda x: next((b["label"] for b in backend_opts if b["id"] == x), x),
    )
    st.caption(
        f"将按当前嵌入模型 **{cur_model}（{cur_dim} 维）** 创建空库；"
        "创建后请切换到此库并在「数据入库」重新上传文档。"
    )
    if st.button("创建向量库", type="primary"):
        if not name.strip():
            st.warning("请填写名称")
        elif _create(api_base, name.strip(), backend):
            st.success("已创建。若需使用，请点击「切换」并重新入库。")
            st.rerun()
        else:
            st.error("创建失败")


if __name__ == "__main__":
    main()
