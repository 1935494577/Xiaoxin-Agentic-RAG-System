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

export default function App() {
  const userId = userIdFromStorage();
  const [nav, setNav] = useState<NavConfig | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [department, setDepartment] = useState("技术");
  const [streamFast, setStreamFast] = useState(true);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamMode, setStreamMode] = useState<"kb" | "general" | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const refreshSessions = useCallback(async () => {
    const rows = await listSessions(userId);
    setSessions(rows);
    return rows;
  }, [userId]);

  useEffect(() => {
    fetchNav().then(setNav).catch(() => setNav(null));
    fetchUiConfig()
      .then((ui) => {
        if (typeof ui.stream_fast_mode === "boolean") {
          setStreamFast(ui.stream_fast_mode);
        }
      })
      .catch(() => undefined);
    refreshSessions().then((rows) => {
      if (rows.length && !sessionId) {
        setSessionId(rows[0].id);
      }
    });
  }, [refreshSessions, sessionId]);

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
    setStreamMode(null);
    setStatus("检索中…");

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
        stream_fast_mode: streamFast,
        skip_query_rewrite: true,
        session_id: sid,
        history: priorHistory,
      },
      (evt: StreamEvent) => {
        if (evt.type === "status") {
          if (evt.phase === "fallback") {
            assistant = "";
            setStreamText("");
          }
          if (evt.answer_mode === "kb" || evt.answer_mode === "general") {
            setStreamMode(evt.answer_mode);
          }
          const mode =
            evt.answer_mode === "general" ? " · 通用" : evt.answer_mode === "kb" ? " · 知识库" : "";
          const phaseLabel =
            evt.phase === "fallback"
              ? "知识库未命中，改用通用回答…"
              : evt.phase === "generating"
                ? "生成中…"
                : "检索中…";
          setStatus(phaseLabel + mode);
        } else if (evt.type === "token") {
          assistant += evt.content;
          setStreamText(assistant);
        } else if (evt.type === "error") {
          setError(evt.message);
        } else if (evt.type === "done") {
          assistant = evt.answer;
          if (evt.answer_mode === "kb" || evt.answer_mode === "general") {
            setStreamMode(evt.answer_mode);
          }
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
    setStreamMode(null);
    setStatus("");
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
        ...(streamText ? [{ role: "assistant" as const, content: streamText }] : []),
      ]
    : messages;

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
          <div className="chat-header">
            <span className="status-line">{status}</span>
            <label>
              <input
                type="checkbox"
                checked={streamFast}
                onChange={(e) => setStreamFast(e.target.checked)}
              />
              快速流式
            </label>
          </div>
          <div className="messages-scroll">
            <div className="messages-inner">
              {!displayMessages.length && !streaming && (
                <div className="welcome">
                  <h2>企业知识库助手</h2>
                  <p>输入问题，助手将基于知识库内容回答</p>
                </div>
              )}
              {displayMessages.map((m, i) => (
                <MessageBubble
                  key={i}
                  message={m}
                  streaming={streaming && i === displayMessages.length - 1 && m.role === "assistant"}
                  streamingMode={
                    streaming && i === displayMessages.length - 1 && m.role === "assistant"
                      ? streamMode
                      : null
                  }
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
          <div className="composer-wrap">
            <div className="composer">
              <textarea
                rows={1}
                value={input}
                placeholder="输入你的问题，助手将基于知识库内容回答"
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
