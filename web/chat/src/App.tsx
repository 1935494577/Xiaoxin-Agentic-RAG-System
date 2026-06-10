import { useCallback, useEffect, useRef, useState } from "react";

import {

  appendMessages,

  createSession,

  deleteSession,

  fetchNav,

  fetchUiConfig,

  listSessions,

  loadMessages,

  streamChat,

  userIdFromStorage,

  type ChatMessage,

  type ChatSession,

  type NavConfig,

  type StreamEvent,

} from "./api/client";

import MessageBubble from "./components/MessageBubble";

import Sidebar from "./components/Sidebar";

import TopNav from "./components/TopNav";



const HYBRID_KEY = "jnao_hybrid_expert_mode";



export default function App() {

  const userId = userIdFromStorage();

  const [nav, setNav] = useState<NavConfig | null>(null);

  const [sessions, setSessions] = useState<ChatSession[]>([]);

  const [sessionId, setSessionId] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [input, setInput] = useState("");

  const [department, setDepartment] = useState("技术");

  const [hybridExpert, setHybridExpert] = useState(false);

  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);

  const [error, setError] = useState("");

  const [streaming, setStreaming] = useState(false);

  const [streamText, setStreamText] = useState("");

  const abortRef = useRef<AbortController | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);



  const refreshSessions = useCallback(async () => {

    const rows = await listSessions(userId);

    setSessions(rows);

    return rows;

  }, [userId]);



  useEffect(() => {

    const stored = localStorage.getItem(HYBRID_KEY);

    if (stored === "1") {

      setHybridExpert(true);

    } else if (stored === "0") {

      setHybridExpert(false);

    }

    fetchNav().then(setNav).catch(() => setNav(null));

    fetchUiConfig()

      .then((ui) => {

        if (stored === null && typeof ui.hybrid_expert_mode === "boolean") {

          setHybridExpert(ui.hybrid_expert_mode);

        }

        if (Array.isArray(ui.suggested_questions)) {

          setSuggestedQuestions(ui.suggested_questions.filter((q) => String(q).trim()).slice(0, 12));

        }

      })

      .catch(() => undefined);

    refreshSessions().then((rows) => {

      if (rows.length && !sessionId) {

        setSessionId(rows[0].id);

      }

    });

  }, [refreshSessions, sessionId]);



  const toggleHybridExpert = (on: boolean) => {

    setHybridExpert(on);

    localStorage.setItem(HYBRID_KEY, on ? "1" : "0");

  };



  useEffect(() => {

    if (!sessionId) {

      setMessages([]);

      return;

    }

    loadMessages(userId, sessionId)

      .then(setMessages)

      .catch(() => setMessages([]));

  }, [sessionId, userId]);



  useEffect(() => {

    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

  }, [messages, streamText, streaming]);



  const handleNew = async () => {

    const s = await createSession(userId);

    await refreshSessions();

    setSessionId(s.id);

    setMessages([]);

  };



  const handleDelete = async () => {

    if (!sessionId || !confirm("确认删除此对话？")) return;

    await deleteSession(userId, sessionId);

    const rows = await refreshSessions();

    const next = rows[0]?.id || null;

    setSessionId(next);

  };



  const handleSend = async () => {

    const text = input.trim();

    if (!text || streaming) return;

    setError("");

    setInput("");



    let sid = sessionId;

    if (!sid) {

      const s = await createSession(userId);

      sid = s.id;

      setSessionId(sid);

      await refreshSessions();

    }



    const userMsg: ChatMessage = { role: "user", content: text };

    setMessages((m) => [...m, userMsg]);

    setStreaming(true);

    setStreamText("");



    const ctrl = new AbortController();

    abortRef.current = ctrl;



    let assistant = "";

    let meta: ChatMessage["meta"] = {};

    const priorHistory = messages.map((m) => ({ role: m.role, content: m.content }));



    await streamChat(

      {

        message: text,

        user_id: userId,

        user_department: department,

        hybrid_expert_mode: hybridExpert,

        skip_query_rewrite: true,

        session_id: sid,

        history: priorHistory,

      },

      (evt: StreamEvent) => {

        if (evt.type === "token") {
          assistant += evt.content;
          setStreamText(assistant);
        } else if (evt.type === "error") {

          setError(evt.message);

        } else if (evt.type === "done") {

          assistant = evt.answer;

          meta = {

            sources: evt.sources,

            source_refs: evt.source_refs,

            answer_mode: evt.answer_mode,

            verified: evt.verified,

            trace_id: evt.trace_id,

          };

        }

      },

      ctrl.signal,

    );



    setStreaming(false);

    setStreamText("");

    abortRef.current = null;



    const finalContent = assistant || error || "（无回复）";

    const assistantMsg: ChatMessage = { role: "assistant", content: finalContent, meta };

    const all = [...messages, userMsg, assistantMsg];

    setMessages(all);

    try {

      await appendMessages(userId, sid!, [userMsg, assistantMsg], text);

      await refreshSessions();

    } catch {

      /* ignore persist errors */

    }

  };



  const displayMessages = streaming

    ? [

        ...messages,

        ...(streamText || streaming ? [{ role: "assistant" as const, content: streamText }] : []),

      ]

    : messages;



  const inputPlaceholder = hybridExpert

    ? "输入问题；优先知识库，必要时补充通用能力"

    : "输入问题，助手将基于知识库内容回答";



  return (

    <div className="app-shell">

      <Sidebar

        sessions={sessions}

        activeId={sessionId}

        onSelect={setSessionId}

        onNew={handleNew}

        onDelete={handleDelete}

        department={department}

        onDepartment={setDepartment}

      />

      <div className="main-column">

        {nav && <TopNav nav={nav} activeId="chat" />}

        <div className="main-panel">

          {error && <div className="error-banner">{error}</div>}

          <div className="messages-scroll">

            <div className="messages-inner">

              {!displayMessages.length && !streaming && (

                <div className="welcome">

                  <h2>Jnao Chat</h2>

                  <p>{inputPlaceholder}</p>

                  {suggestedQuestions.length > 0 && (

                    <div className="welcome-suggestions">

                      {suggestedQuestions.map((q) => (

                        <button

                          key={q}

                          type="button"

                          className="suggestion-chip"

                          onClick={() => setInput(q)}

                          disabled={streaming}

                        >

                          {q}

                        </button>

                      ))}

                    </div>

                  )}

                </div>

              )}

              {displayMessages.map((m, i) => (

                <MessageBubble

                  key={i}

                  message={m}

                  hideModeTag

                  streaming={streaming && i === displayMessages.length - 1 && m.role === "assistant"}

                />

              ))}

              <div ref={messagesEndRef} />

            </div>

          </div>

          <div className="composer-wrap">

            <div className="composer-toolbar">

              <label className="mode-switch" title="开启后优先检索知识库，未命中时自动使用通用能力">

                <span className="mode-switch-label">混合专家模式</span>

                <button

                  type="button"

                  role="switch"

                  aria-checked={hybridExpert}

                  className={"mode-switch-btn" + (hybridExpert ? " on" : "")}

                  onClick={() => toggleHybridExpert(!hybridExpert)}

                  disabled={streaming}

                >

                  <span className="mode-switch-knob" />

                </button>

              </label>

              <span className="mode-switch-hint">

                {hybridExpert ? "知识库优先 · 可补充通用回答" : "仅知识库检索"}

              </span>

            </div>

            <div className="composer">

              <textarea

                rows={1}

                value={input}

                placeholder={inputPlaceholder}

                onChange={(e) => setInput(e.target.value)}

                onKeyDown={(e) => {

                  if (e.key === "Enter" && !e.shiftKey) {

                    e.preventDefault();

                    handleSend();

                  }

                }}

                disabled={streaming}

              />

              {streaming ? (

                <button type="button" className="stop" onClick={() => abortRef.current?.abort()}>

                  停止

                </button>

              ) : (

                <button type="button" className="send" disabled={!input.trim()} onClick={handleSend}>

                  发送

                </button>

              )}

            </div>

            <div className="composer-hint">Enter 发送 · Shift+Enter 换行</div>

          </div>

        </div>

      </div>

    </div>

  );

}


