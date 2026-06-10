"""提示词配置 — 可插拔 System Prompt 分层管理。"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import streamlit as st

_FRONT = Path(__file__).resolve().parent.parent
if str(_FRONT) not in sys.path:
    sys.path.insert(0, str(_FRONT))
from _bootstrap import load_streamlit_common  # noqa: E402
from page_init import init_app_page, invalidate_page_cache  # noqa: E402

scom = load_streamlit_common(_FRONT)

_SCOPE_LABELS = {"all": "全部场景", "kb": "知识库", "general": "通用回答"}
_CATEGORY_ORDER = ["persona", "policy", "task", "output", "custom"]
_SLOT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _fetch_prompts(api_base: str, auth: dict[str, str], *, mode: str, fast: bool) -> dict[str, Any] | None:
    try:
        with scom.http_client(api_base, timeout=15.0) as c:
            r = c.get("/config/prompts", params={"mode": mode, "fast": fast}, headers=auth)
            if r.status_code == 200:
                return r.json()
    except Exception:
        return None
    return None


def _group_slots(slots: list[dict[str, Any]], categories: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {k: [] for k in _CATEGORY_ORDER}
    for slot in sorted(slots, key=lambda s: (int(s.get("order") or 0), str(s.get("id") or ""))):
        cat = str(slot.get("category") or "custom")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(slot)
    for cat in list(grouped.keys()):
        if not grouped[cat]:
            del grouped[cat]
    return grouped


def main() -> None:
    if "rag_api_base" not in st.session_state:
        st.session_state.rag_api_base = scom.DEFAULT_API

    api_base = scom.get_api_base()
    auth = scom.get_api_auth_headers()
    prof_data = scom.fetch_model_profiles(api_base)
    init_app_page(api_base, auth, prof_data, check_model_status=False, nav_id="prompts")

    st.title("提示词")
    st.caption(
        "按标准 Prompt 工程分层配置 System Prompt：角色人设 → 行为约束 → 任务指令 → 输出格式。"
        " 各层可独立启用/禁用，保存后立即作用于 Jnao Chat。"
    )

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        preview_mode = st.selectbox("预览场景", ["kb", "general"], format_func=lambda x: "知识库" if x == "kb" else "通用回答")
    with c2:
        preview_fast = st.toggle("快速流式", value=True, disabled=preview_mode != "kb")
    with c3:
        st.markdown(
            "**组合顺序**：按 `order` 从小到大拼接已启用层；"
            "知识库快速模式会使用「任务（快速）」替代「任务（标准）」。"
        )

    data = _fetch_prompts(api_base, auth, mode=preview_mode, fast=preview_fast and preview_mode == "kb")
    if not data:
        st.error("无法加载提示词配置，请确认 API 已启动。")
        return

    categories = data.get("categories") or {}
    slots: list[dict[str, Any]] = list(data.get("slots") or [])
    grouped = _group_slots(slots, categories)

    edited: list[dict[str, Any]] = []

    for cat in _CATEGORY_ORDER:
        rows = grouped.get(cat) or []
        if not rows:
            continue
        cat_label = categories.get(cat) or cat
        st.subheader(cat_label)
        for slot in rows:
            sid = str(slot.get("id") or "")
            builtin = bool(slot.get("builtin"))
            title = str(slot.get("label") or sid)
            desc = str(slot.get("description") or "")
            with st.expander(f"{'🔒 ' if builtin else '➕ '}{title} (`{sid}`)", expanded=(cat == "persona")):
                if desc:
                    st.caption(desc)
                enabled = st.toggle("启用", value=bool(slot.get("enabled", True)), key=f"en_{sid}")
                order = st.number_input("顺序 (order)", min_value=0, max_value=9999, value=int(slot.get("order") or 100), key=f"ord_{sid}")
                scope_raw = slot.get("scope") or ["all"]
                if isinstance(scope_raw, str):
                    scope_raw = [scope_raw]
                scope = st.multiselect(
                    "适用场景 (scope)",
                    options=["all", "kb", "general"],
                    default=[s for s in scope_raw if s in ("all", "kb", "general")] or ["all"],
                    format_func=lambda x: _SCOPE_LABELS.get(x, x),
                    key=f"scope_{sid}",
                )
                if not builtin:
                    label = st.text_input("显示名称", value=title, key=f"label_{sid}")
                else:
                    label = title
                content = st.text_area(
                    "提示词内容",
                    value=str(slot.get("content") or ""),
                    height=140,
                    key=f"txt_{sid}",
                )
                edited.append(
                    {
                        "id": sid,
                        "label": label,
                        "description": str(slot.get("description") or ""),
                        "category": cat,
                        "scope": scope or ["all"],
                        "enabled": enabled,
                        "order": int(order),
                        "content": content,
                        "builtin": builtin,
                        **({"variant": slot.get("variant")} if slot.get("variant") else {}),
                    }
                )

    st.divider()
    st.subheader("添加自定义层")
    with st.form("add_prompt_slot", clear_on_submit=True):
        new_id = st.text_input("ID（小写英文+下划线）", placeholder="例如：compliance_policy")
        new_label = st.text_input("显示名称", placeholder="例如：合规约束")
        new_scope = st.multiselect("适用场景", ["all", "kb", "general"], default=["all"], format_func=lambda x: _SCOPE_LABELS.get(x, x))
        new_content = st.text_area("提示词内容", height=100)
        add_btn = st.form_submit_button("添加")
        if add_btn:
            nid = (new_id or "").strip().lower()
            if not _SLOT_ID_RE.match(nid):
                st.error("ID 格式无效：需以小写字母开头，仅含 a-z、0-9、下划线。")
            elif any(s.get("id") == nid for s in slots):
                st.error("ID 已存在。")
            elif not (new_content or "").strip():
                st.error("内容不能为空。")
            else:
                edited.append(
                    {
                        "id": nid,
                        "label": (new_label or nid).strip(),
                        "description": "",
                        "category": "custom",
                        "scope": new_scope or ["all"],
                        "enabled": True,
                        "order": 100,
                        "content": new_content.strip(),
                        "builtin": False,
                    }
                )
                try:
                    with scom.http_client(api_base, timeout=15.0) as c:
                        r = c.put(
                            "/config/prompts",
                            json={"slots": edited},
                            params={"mode": preview_mode, "fast": preview_fast and preview_mode == "kb"},
                            headers=auth,
                        )
                    if r.status_code == 200:
                        invalidate_page_cache()
                        st.success("已添加自定义层")
                        st.rerun()
                    else:
                        st.error(r.text[:400])
                except Exception as e:
                    st.error(str(e))

    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("保存全部", type="primary"):
            try:
                with scom.http_client(api_base, timeout=15.0) as c:
                    r = c.put(
                        "/config/prompts",
                        json={"slots": edited},
                        params={"mode": preview_mode, "fast": preview_fast and preview_mode == "kb"},
                        headers=auth,
                    )
                if r.status_code == 200:
                    invalidate_page_cache()
                    st.success("已保存")
                    st.rerun()
                else:
                    st.error(r.text[:400])
            except Exception as e:
                st.error(str(e))
    with col_reset:
        if st.button("恢复内置默认"):
            try:
                with scom.http_client(api_base, timeout=15.0) as c:
                    r = c.put(
                        "/config/prompts",
                        json={"reset_defaults": True},
                        params={"mode": preview_mode, "fast": preview_fast and preview_mode == "kb"},
                        headers=auth,
                    )
                if r.status_code == 200:
                    invalidate_page_cache()
                    st.success("已恢复默认")
                    st.rerun()
                else:
                    st.error(r.text[:400])
            except Exception as e:
                st.error(str(e))

    preview = data.get("preview") or {}
    st.divider()
    st.subheader("合成预览")
    layers = preview.get("layers") or []
    if layers:
        for layer in layers:
            st.markdown(f"**{layer.get('label')}** (`{layer.get('category')}`)")
            st.code(str(layer.get("content") or ""), language=None)
    composed = str(preview.get("composed") or "")
    if composed:
        st.text_area("最终 System Prompt", value=composed, height=220, disabled=True)


if __name__ == "__main__":
    main()
