"""RAG 对话 — 企业级单卡片布局。"""



from __future__ import annotations



import json

import sys

from pathlib import Path

from typing import Any, Iterator



import httpx

import streamlit as st



_FRONT = Path(__file__).resolve().parent.parent

if str(_FRONT) not in sys.path:

    sys.path.insert(0, str(_FRONT))

from _bootstrap import load_streamlit_common  # noqa: E402

from chat_sessions import (

    append_messages,

    create_session,

    delete_session,

    list_sessions,

    load_messages,

)

from chat_ui import (

    message_bubble_html,

    render_chat_panel,

    render_streaming_assistant,

    user_facing_error,

)

from page_init import init_app_page  # noqa: E402

from user_profile import (

    get_dept_code,

    get_user_display_name,

    get_user_id,

    init_user_profile_state,

    on_user_identity_changed,

)



scom = load_streamlit_common(_FRONT)





def _chat_department() -> str:

    return get_dept_code()





def _sync_user_chat_binding() -> str:

    uid = get_user_id()

    key = f"{uid}|{get_user_display_name()}|{_chat_department()}"

    if st.session_state.get("_chat_user_key") != key:

        st.session_state["_chat_user_key"] = key

        on_user_identity_changed()

    return uid





def _ensure_chat_session(api_base: str, user_id: str) -> str | None:

    sid = str(st.session_state.get("chat_session_id") or "").strip()

    if sid:

        return sid

    sessions = list_sessions(api_base, user_id)

    if sessions:

        sid = sessions[0]["id"]

    else:

        created = create_session(api_base, user_id)

        if not created:

            return None

        sid = created["id"]

    st.session_state.chat_session_id = sid

    if "messages" not in st.session_state:

        st.session_state.messages = load_messages(api_base, user_id, sid)

    return sid





def _load_session_messages(api_base: str, user_id: str, session_id: str) -> None:

    st.session_state.chat_session_id = session_id

    st.session_state.messages = load_messages(api_base, user_id, session_id)





def _persist_stream_fast_mode(api_base: str) -> None:

    try:

        with scom.http_client(api_base, timeout=10.0) as c:

            c.put("/config/ui", json={"stream_fast_mode": bool(st.session_state.get("stream_fast_mode", False))})

    except Exception:

        pass





def _render_stream_mode_toggle(ui: dict[str, Any], api_base: str) -> bool:

    if "stream_fast_mode" not in st.session_state:

        st.session_state.stream_fast_mode = bool(ui.get("stream_fast_mode", False))

    with st.sidebar:

        st.markdown("**回答模式**")

        st.toggle(

            "快速流式",

            key="stream_fast_mode",

            help="开启：更快首字（跳过重排、少检索）。关闭：标准模式，完整检索+重排，更准确。",

            on_change=_persist_stream_fast_mode,

            args=(api_base,),

        )

        mode = "快速" if st.session_state.stream_fast_mode else "标准"

        st.caption(f"当前：{mode}流式")

    return bool(st.session_state.stream_fast_mode)





def _render_session_sidebar(api_base: str, user_id: str) -> None:

    with st.sidebar:

        st.markdown("**对话历史**")

        sessions = list_sessions(api_base, user_id)

        if not sessions:

            if st.button("新建对话", key="chat_new_empty", use_container_width=True):

                created = create_session(api_base, user_id)

                if created:

                    _load_session_messages(api_base, user_id, created["id"])

                    st.rerun()

            return



        current = str(st.session_state.get("chat_session_id") or sessions[0]["id"])

        labels = {s["id"]: s.get("title") or "新对话" for s in sessions}

        ids = [s["id"] for s in sessions]

        if current not in ids:

            current = ids[0]



        def _fmt(sid: str) -> str:

            return labels.get(sid, sid[:8])



        picked = st.selectbox(

            "会话",

            ids,

            index=ids.index(current),

            format_func=_fmt,

            key="chat_session_picker",

            label_visibility="collapsed",

        )

        if picked != st.session_state.get("chat_session_id"):

            _load_session_messages(api_base, user_id, picked)

            st.rerun()



        c1, c2 = st.columns(2)

        with c1:

            if st.button("新建", key="chat_new", use_container_width=True):

                created = create_session(api_base, user_id)

                if created:

                    _load_session_messages(api_base, user_id, created["id"])

                    st.rerun()

        with c2:

            if st.button("删除", key="chat_del", use_container_width=True):

                if delete_session(api_base, user_id, picked):

                    st.session_state.pop("chat_session_id", None)

                    st.session_state.messages = []

                    st.rerun()





def _iter_stream_events(api_base: str, payload: dict[str, Any]) -> Iterator[dict[str, Any]]:

    with scom.http_client(api_base, timeout=300.0) as client:

        with client.stream("POST", "/chat/stream", json=payload) as resp:

            if resp.status_code != 200:

                body = resp.read().decode("utf-8", errors="ignore")

                yield {"type": "error", "message": user_facing_error(body)}

                return

            for line in resp.iter_lines():

                if not line or not line.startswith("data: "):

                    continue

                try:

                    yield json.loads(line[6:])

                except json.JSONDecodeError:

                    continue





def _render_suggestions(suggestions: list[str]) -> None:

    if not suggestions:

        return

    st.markdown('<div class="suggest-wrap">', unsafe_allow_html=True)

    cols = st.columns(min(len(suggestions), 3))

    for i, q in enumerate(suggestions):

        with cols[i % len(cols)]:

            if st.button(q, key=f"suggest_{i}", use_container_width=True):

                st.session_state.pending_prompt = q

                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)





def main() -> None:

    if "rag_api_base" not in st.session_state:

        st.session_state.rag_api_base = scom.DEFAULT_API

    init_user_profile_state()

    user_id = _sync_user_chat_binding()



    api_base = scom.get_api_base()

    auth = scom.get_api_auth_headers()

    prof_data = scom.fetch_model_profiles(api_base)

    ui, model_profile_id, force_env = init_app_page(

        api_base, auth, prof_data, check_model_status=False

    )



    session_id = _ensure_chat_session(api_base, user_id)

    stream_fast = _render_stream_mode_toggle(ui, api_base)

    _render_session_sidebar(api_base, user_id)



    if "messages" not in st.session_state:

        st.session_state.messages = []



    title = str(ui.get("app_title") or "企业知识库助手")

    tagline = str(ui.get("app_tagline") or "把文档放进知识库，用自然语言提问；无需编写代码。")

    suggestions = [str(q).strip() for q in (ui.get("suggested_questions") or []) if str(q).strip()][:6]



    render_chat_panel(

        st.session_state.messages,

        show_welcome=True,

        tagline=tagline,

        title=title,

    )



    if not st.session_state.messages and suggestions:

        _render_suggestions(suggestions)



    prompt = st.session_state.pop("pending_prompt", None) or st.chat_input(

        "输入你的问题，助手将基于知识库内容回答"

    )



    if not prompt:

        return



    st.session_state.messages.append({"role": "user", "content": prompt})



    if not scom.ping_health_fast(api_base):

        st.session_state.messages.append({"role": "assistant", "content": scom.SERVICE_UNAVAILABLE})

        if session_id:

            append_messages(

                api_base,

                user_id,

                session_id,

                st.session_state.messages[-2:],

                auto_title_from=prompt,

            )

        st.rerun()



    payload: dict[str, Any] = {

        "message": prompt,

        "user_id": user_id,

        "user_department": _chat_department(),

        "allowed_sources": None,

        "model_profile_id": model_profile_id,

        "force_env_llm": force_env,

        "temperature": 0.2,

        "skip_query_rewrite": True,

        "stream_fast_mode": stream_fast,

    }



    render_chat_panel(

        st.session_state.messages[:-1],

        show_welcome=False,

        tagline=tagline,

        title=title,

        append_html=message_bubble_html("user", get_user_display_name(), prompt),

    )



    placeholder = st.empty()

    full = ""

    meta: dict[str, Any] = {}

    phase = "retrieving"

    render_streaming_assistant(placeholder, full, phase=phase)



    try:

        for evt in _iter_stream_events(api_base, payload):

            if evt.get("type") == "status":

                phase = str(evt.get("phase") or "generating")

                render_streaming_assistant(placeholder, full, phase=phase)

            elif evt.get("type") == "token":

                full += str(evt.get("content") or "")

                render_streaming_assistant(placeholder, full, phase="generating")

            elif evt.get("type") == "done":

                full = str(evt.get("answer") or full)

                meta = {

                    "sources": evt.get("sources"),

                    "source_refs": evt.get("source_refs"),

                }

            elif evt.get("type") == "error":

                full = user_facing_error(str(evt.get("message") or ""))

                break

        placeholder.markdown(

            message_bubble_html("assistant", "企业知识库助手", full or "暂未找到相关内容。", meta=meta or None),

            unsafe_allow_html=True,

        )

    except (httpx.TimeoutException, httpx.ConnectError):

        full = scom.SERVICE_UNAVAILABLE

        render_streaming_assistant(placeholder, full)

    except Exception:

        full = "处理出现问题，请稍后重试。"

        render_streaming_assistant(placeholder, full)



    assistant_msg: dict[str, Any] = {"role": "assistant", "content": full, "meta": meta or None}

    st.session_state.messages.append(assistant_msg)



    if session_id:

        append_messages(

            api_base,

            user_id,

            session_id,

            [

                {"role": "user", "content": prompt},

                {"role": "assistant", "content": full, "meta": meta or None},

            ],

            auto_title_from=prompt,

        )



    st.rerun()





if __name__ == "__main__":

    main()

