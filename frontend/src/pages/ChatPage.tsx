import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  appendMessages,
  createSession,
  deleteSession,
  fetchUiConfig,
  listSessions,
  loadMessages,
  streamChat,
} from "../api/client";
import { HYBRID_MODE_KEY } from "../lib/constants";
import { useAuth } from "../hooks/useAuth";
import { useLocalStorage } from "../hooks/useLocalStorage";
import { useUserProfile } from "../context/UserProfileContext";
import type { ChatMessage, ChatSession, StreamEvent, ToolTraceItem } from "../api/types";
import { applyToolStreamEvent } from "../lib/streamTools";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { ChatInput } from "../components/chat/ChatInput";
import { ChatToolbar } from "../components/chat/ChatToolbar";
import { SessionList } from "../components/chat/SessionList";
import MessageBubble from "../components/chat/MessageBubble";

const SUGGESTIONS_FALLBACK = [
  "1-3年级超脑阅读要求是什么？",
  "把文档放进知识库后如何提问？",
  "支持哪些文件格式入库？",
];

export default function ChatPage() {
  const { userId } = useAuth();
  const { department, displayName, avatarUrl, aiDisplayName, aiAvatarUrl } = useUserProfile();

  const [sidebarOpen, setSidebarOpen] = useState(true);

  // ---- session state ----
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // ---- message state (local, like old App.tsx) ----
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamTools, setStreamTools] = useState<ToolTraceItem[]>([]);
  const [error, setError] = useState("");

  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const initDone = useRef(false);

  const [input, setInput] = useState("");
  const [newTopicPending, setNewTopicPending] = useState(false);
  const [hybridExpert, setHybridExpert] = useLocalStorage<boolean>(HYBRID_MODE_KEY, false);

  const { data: uiConfig } = useQuery({
    queryKey: ["uiConfig"],
    queryFn: fetchUiConfig,
    staleTime: 300_000,
  });

  // ---- refresh sessions imperatively (like old App.tsx) ----
  const refreshSessions = useCallback(async () => {
    try {
      const rows = await listSessions(userId);
      setSessions(rows);
      return rows;
    } catch (err) {
      console.error("获取会话列表失败", err);
      return [];
    }
  }, [userId]);

  // ---- init: load sessions + uiConfig (matches old App.tsx timing) ----
  useEffect(() => {
    if (initDone.current) return;

    const stored = localStorage.getItem(HYBRID_MODE_KEY);
    if (stored === "1") setHybridExpert(true);
    else if (stored === "0") setHybridExpert(false);

    refreshSessions().then((rows) => {
      if (rows && rows.length && !sessionId) {
        setSessionId(rows[0].id);
      }
      initDone.current = true;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Apply uiConfig hybrid default on first load
  useEffect(() => {
    if (!uiConfig || typeof uiConfig.hybrid_expert_mode !== "boolean") return;
    const stored = localStorage.getItem(HYBRID_MODE_KEY);
    if (stored === null) {
      setHybridExpert(uiConfig.hybrid_expert_mode);
    }
  }, [uiConfig, setHybridExpert]);

  // ---- load messages when session changes (like old App.tsx) ----
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    loadMessages(userId, sessionId)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, [sessionId, userId]);

  // ---- auto-scroll ----
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText, streaming]);

  // ---- session CRUD ----
  const handleNew = async () => {
    const s = await createSession(userId);
    await refreshSessions();
    setSessionId(s.id);
  };

  const handleDelete = async () => {
    if (!sessionId || !confirm("确认删除此对话？")) return;
    await deleteSession(userId, sessionId);
    const rows = await refreshSessions();
    setSessionId(rows[0]?.id || null);
  };

  // ---- send message (follows old App.tsx pattern exactly) ----
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

    // 1. Add user message to display IMMEDIATELY
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);

    // 2. Start streaming
    setStreaming(true);
    setStreamText("");
    setStreamTools([]);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    let assistant = "";
    let meta: ChatMessage["meta"] = {};
    let toolTrace: ToolTraceItem[] = [];
    const priorHistory = newTopicPending
      ? []
      : messages.map((m) => ({ role: m.role, content: m.content }));
    const resetContext = newTopicPending;

    await streamChat(
      {
        message: text,
        user_id: userId,
        user_department: department,
        hybrid_expert_mode: hybridExpert,
        skip_query_rewrite: true,
        session_id: sid,
        history: priorHistory,
        reset_context: resetContext,
      },
      (evt: StreamEvent) => {
        if (evt.type === "token") {
          assistant += evt.content;
          setStreamText(assistant);
        } else if (evt.type === "tool_call" || evt.type === "tool_result") {
          toolTrace = applyToolStreamEvent(toolTrace, evt);
          setStreamTools(toolTrace);
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
            tool_trace: evt.tool_trace?.length ? evt.tool_trace : toolTrace,
          };
        }
      },
      ctrl.signal
    );

    // 3. Stream finished
    setStreaming(false);
    setStreamText("");
    setStreamTools([]);
    abortRef.current = null;
    setNewTopicPending(false);

    const finalContent = assistant || error || "（无回复）";
    const assistantMsg: ChatMessage = {
      role: "assistant",
      content: finalContent,
      meta,
    };

    const all = [...messages, userMsg, assistantMsg];
    setMessages(all);

    // 4. Persist to backend + refresh session list
    try {
      await appendMessages(userId, sid!, [userMsg, assistantMsg], text);
      await refreshSessions();
    } catch (err) {
      console.error("消息持久化失败", err);
    }
  };

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // ---- derived display (computed during render, NOT via useEffect - matches old App.tsx) ----
  // Always append a streaming placeholder bubble so the AI avatar and "…"
  // thinking indicator appear immediately (before the first token lands).
  const displayMessages: ChatMessage[] = streaming
    ? [...messages, { role: "assistant" as const, content: streamText }]
    : messages;

  // ---- UI data ----
  const suggestedQuestions =
    uiConfig?.suggested_questions?.filter((q) => String(q).trim()).slice(0, 12) ||
    SUGGESTIONS_FALLBACK;

  const inputPlaceholder = hybridExpert
    ? "输入问题；优先知识库，必要时补充通用能力"
    : "输入问题，助手将基于知识库内容回答";

  return (
    <div className="flex h-full">
      <div
        className={
          "shrink-0 overflow-hidden transition-all duration-300 ease-in-out " +
          (sidebarOpen ? "w-[260px]" : "w-[40px]")
        }
      >
        {sidebarOpen ? (
          <div className="relative h-full">
            <SessionList
              sessions={sessions}
              activeId={sessionId}
              onSelect={setSessionId}
              onNew={handleNew}
              onDelete={handleDelete}
            />
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="absolute right-2 top-4 z-10 p-1 rounded-lg text-text-muted hover:text-text hover:bg-border/50 transition-colors cursor-pointer"
              title="收起侧边栏"
            >
              <PanelLeftClose size={18} />
            </button>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center pt-4 bg-surface-muted border-r border-border">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="p-1 rounded-lg text-text-muted hover:text-text hover:bg-border/50 transition-colors cursor-pointer"
              title="展开侧边栏"
            >
              <PanelLeftOpen size={18} />
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        {error && (
          <div className="bg-error-bg text-error text-sm text-center py-2">{error}</div>
        )}

        <div className="flex-1 overflow-y-auto bg-white chat-scroll-area px-4 sm:px-6 pt-16 pb-4">
          <div className="min-h-full flex flex-col pb-2">
            {!displayMessages.length && !streaming && (
              <div className="max-w-[480px] mx-auto my-auto text-center py-12">
                <h2 className="text-[#1a1d21] font-semibold text-xl mb-3">Jnao Chat</h2>
                <p className="text-text-muted mb-5">{inputPlaceholder}</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {suggestedQuestions.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => setInput(q)}
                      disabled={streaming}
                      className="border border-border bg-surface-muted text-text rounded-full px-3.5 py-2 text-[13px] leading-relaxed cursor-pointer hover:border-brand hover:bg-brand-light disabled:opacity-60 disabled:cursor-not-allowed max-w-full text-left transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {displayMessages.map((m, i) => {
              let questionForFeedback: string | undefined;
              if (m.role === "assistant") {
                for (let j = i - 1; j >= 0; j--) {
                  if (displayMessages[j].role === "user") {
                    questionForFeedback = displayMessages[j].content;
                    break;
                  }
                }
              }
              return (
                <MessageBubble
                  key={m.id || i}
                  message={m}
                  hideModeTag
                  sessionId={sessionId ?? undefined}
                  questionForFeedback={questionForFeedback}
                  userAvatar={avatarUrl}
                  userDisplayName={displayName}
                  aiAvatar={aiAvatarUrl}
                  aiDisplayName={aiDisplayName}
                  liveTools={
                    streaming && i === displayMessages.length - 1 && m.role === "assistant"
                      ? streamTools
                      : undefined
                  }
                  streaming={streaming && i === displayMessages.length - 1 && m.role === "assistant"}
                />
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="border-t border-border bg-white px-5 pt-3 pb-5">
          <div className="mb-2.5">
            <ChatToolbar
              hybridExpert={hybridExpert}
              onHybridChange={setHybridExpert}
              newTopicPending={newTopicPending}
              onNewTopicToggle={() => setNewTopicPending((v) => !v)}
              streaming={streaming}
            />
          </div>
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={handleSend}
            streaming={streaming}
            onStop={abort}
            placeholder={inputPlaceholder}
          />
          <p className="max-w-[768px] mx-auto mt-2 text-xs text-center text-text-muted">
            Enter 发送 · Shift+Enter 换行
          </p>
        </div>
      </div>
    </div>
  );
}
