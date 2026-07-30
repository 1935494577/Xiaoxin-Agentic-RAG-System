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
import { resolveStreamFastMode } from "../lib/chatDefaults";
import {
  loadStoredAssistantMode,
  normalizeAssistantMode,
  placeholderForMode,
  saveStoredAssistantMode,
  type AssistantMode,
} from "../lib/assistantMode";
import { useAuth } from "../hooks/useAuth";
import { useUserProfile } from "../context/UserProfileContext";
import type {
  ChatMessage,
  ChatSession,
  ClarifyOption,
  GraphViz,
  StreamEvent,
  ToolTraceItem,
} from "../api/types";
import { type ExecutionStep } from "../lib/executionTimeline";
import { reduceStreamTurnEvent } from "../lib/chatStreamTurn";
import { downloadMarkdown, messagesToMarkdown } from "../lib/exportChatMarkdown";
import { toast } from "sonner";
import { PanelLeftClose, PanelLeftOpen, Sparkles } from "lucide-react";
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
  const [streamExecutionSteps, setStreamExecutionSteps] = useState<ExecutionStep[]>([]);
  const [streamGraphViz, setStreamGraphViz] = useState<GraphViz | null>(null);
  const [error, setError] = useState("");

  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const [input, setInput] = useState("");
  const [newTopicPending, setNewTopicPending] = useState(false);
  const [clarifyPending, setClarifyPending] = useState<{
    message: string;
    prompt: string;
    options: ClarifyOption[];
    sessionId: string;
  } | null>(null);
  const [assistantMode, setAssistantMode] = useState<AssistantMode>("knowledge");

  const { data: uiConfig } = useQuery({
    queryKey: ["uiConfig", userId],
    queryFn: fetchUiConfig,
    enabled: Boolean(userId),
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

  // Load sessions once auth userId is ready (fixes empty list after LAN login).
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    refreshSessions().then((rows) => {
      if (cancelled || !rows?.length) return;
      setSessionId((current) => current || rows[0].id);
    });
    return () => {
      cancelled = true;
    };
  }, [userId, refreshSessions]);


  useEffect(() => {
    if (!uiConfig) return;
    const stored = loadStoredAssistantMode();
    if (stored != null) {
      setAssistantMode(stored);
      return;
    }
    setAssistantMode(normalizeAssistantMode(uiConfig.default_assistant_mode ?? "knowledge"));
  }, [uiConfig?.default_assistant_mode, uiConfig]);

  const handleAssistantModeChange = useCallback((mode: AssistantMode) => {
    setAssistantMode(mode);
    saveStoredAssistantMode(mode);
  }, []);

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

  const handleExport = useCallback(() => {
    if (!messages.length) {
      toast.message("当前对话为空，无法导出");
      return;
    }
    const session = sessions.find((s) => s.id === sessionId);
    const md = messagesToMarkdown(messages, session);
    const name = (session?.title || "对话").replace(/[\\/:*?"<>|]/g, "_").slice(0, 40);
    downloadMarkdown(`${name}.md`, md);
    toast.success("已导出 Markdown");
  }, [messages, sessionId, sessions]);

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
  const runChatTurn = async (
    text: string,
    opts?: { clarifyChoiceId?: string; appendUser?: boolean; sessionId?: string }
  ) => {
    if (streaming) return;

    setError("");
    setClarifyPending(null);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    let sid = opts?.sessionId || sessionId;
    if (!sid) {
      const s = await createSession(userId);
      sid = s.id;
      setSessionId(sid);
      await refreshSessions();
    }

    const userMsg: ChatMessage = { role: "user", content: text };
    if (opts?.appendUser !== false) {
      setMessages((m) => [...m, userMsg]);
    }

    setStreaming(true);
    setStreamText("");
    setStreamExecutionSteps([]);
    setStreamGraphViz(null);

    let assistant = "";
    let streamError = "";
    let meta: ChatMessage["meta"] = {};
    let toolTrace: ToolTraceItem[] = [];
    let executionSteps: ExecutionStep[] = [];
    let graphViz: GraphViz | undefined;
    let clarifyEvt: Extract<StreamEvent, { type: "clarify" }> | null = null;
    let needsClarify = false;
    const priorHistory = newTopicPending
      ? []
      : messages.map((m) => ({ role: m.role, content: m.content }));
    const resetContext = newTopicPending;

    try {
      await streamChat(
        {
          message: text,
          user_id: userId,
          user_department: department,
          stream_fast_mode: resolveStreamFastMode(uiConfig),
          skip_query_rewrite: true,
          session_id: sid,
          history: priorHistory,
          reset_context: resetContext,
          rag_architecture: "auto",
          assistant_mode: assistantMode,
          clarify_choice_id: opts?.clarifyChoiceId,
        },
        (evt: StreamEvent) => {
          const acc = reduceStreamTurnEvent(
            {
              assistant,
              streamError,
              meta,
              toolTrace,
              executionSteps,
              graphViz,
              needsClarify,
              clarifyEvt,
            },
            evt,
            assistantMode
          );
          assistant = acc.assistant;
          streamError = acc.streamError;
          meta = acc.meta;
          toolTrace = acc.toolTrace;
          executionSteps = acc.executionSteps;
          graphViz = acc.graphViz;
          needsClarify = acc.needsClarify;
          clarifyEvt = acc.clarifyEvt;

          if (evt.type === "token") {
            setStreamText(assistant);
          } else if (evt.type === "graph_viz") {
            setStreamGraphViz(evt.graph);
          } else if (evt.type === "error") {
            setError(evt.message);
          } else if (
            evt.type === "tool_call" ||
            evt.type === "tool_result" ||
            evt.type === "status" ||
            evt.type === "done"
          ) {
            setStreamExecutionSteps([...executionSteps]);
          }
        },
        ctrl.signal
      );
    } catch (err) {
      if (!ctrl.signal.aborted) {
        streamError = err instanceof Error ? err.message : "请求失败";
        setError(streamError);
      }
    } finally {
      setStreaming(false);
      setStreamText("");
      setStreamExecutionSteps([]);
      setStreamGraphViz(null);
      abortRef.current = null;
      setNewTopicPending(false);
    }

    const wasAborted = ctrl.signal.aborted;

    if (wasAborted) {
      const stopped = assistant.trim() ? `${assistant.trim()}\n\n（已停止生成）` : "（已停止生成）";
      setMessages((prev) => [...prev, { role: "assistant", content: stopped, meta }]);
      return;
    }

    if (needsClarify && clarifyEvt) {
      setClarifyPending({
        message: text,
        prompt: clarifyEvt.prompt,
        options: clarifyEvt.options,
        sessionId: sid,
      });
      return;
    }

    const finalContent = assistant || streamError || "（无回复）";
    const assistantMsg: ChatMessage = {
      role: "assistant",
      content: finalContent,
      meta,
    };

    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const toPersist =
        opts?.appendUser === false ? [assistantMsg] : [userMsg, assistantMsg];
      await appendMessages(userId, sid!, toPersist, text);
      await refreshSessions();
    } catch (err) {
      console.error("消息持久化失败", err);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    await runChatTurn(text);
  };

  const handleClarifyPick = async (choiceId: string) => {
    if (!clarifyPending || streaming) return;
    const { message, sessionId: sid } = clarifyPending;
    setClarifyPending(null);
    await runChatTurn(message, {
      clarifyChoiceId: choiceId,
      appendUser: false,
      sessionId: sid,
    });
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

  const inputPlaceholder = placeholderForMode(assistantMode);

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
              <div className="chat-empty-state mx-auto my-auto max-w-lg py-12 text-center">
                <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-light text-brand">
                  <Sparkles className="h-6 w-6" aria-hidden />
                </div>
                <h2 className="text-balance text-xl font-semibold text-text">
                  {displayName ? `${displayName}，你好` : "Jnao Chat"}
                </h2>
                <p className="mx-auto mt-2 max-w-md text-pretty text-sm leading-relaxed text-text-muted">
                  {inputPlaceholder}
                </p>
                <p className="mt-1 text-xs text-text-muted/80">
                  部门：{department || "未设置"} · 回答将基于可见知识库范围
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {suggestedQuestions.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => setInput(q)}
                      disabled={streaming}
                      className="chat-suggestion-chip max-w-full cursor-pointer rounded-full border border-border bg-surface px-3.5 py-2 text-left text-[13px] leading-relaxed text-text transition-colors hover:border-brand hover:bg-brand-light disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {clarifyPending && !streaming && (
              <div className="mx-auto my-4 max-w-xl rounded-2xl border border-brand/30 bg-brand-light/40 px-4 py-4">
                <p className="text-sm font-medium text-text">{clarifyPending.prompt}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {clarifyPending.options.map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => handleClarifyPick(opt.id)}
                      className="chat-suggestion-chip cursor-pointer rounded-full border border-border bg-white px-3.5 py-2 text-left text-[13px] text-text transition-colors hover:border-brand hover:bg-brand-light"
                    >
                      {opt.label}
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
                  userDepartment={department}
                  streaming={streaming && i === displayMessages.length - 1 && m.role === "assistant"}
                  graphViz={
                    streaming && i === displayMessages.length - 1 && m.role === "assistant"
                      ? streamGraphViz
                      : undefined
                  }
                />
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="border-t border-border bg-white px-5 pt-3 pb-5">
          <div className="mb-2.5">
            <ChatToolbar
              assistantMode={assistantMode}
              onAssistantModeChange={handleAssistantModeChange}
              department={department}
              sessionId={sessionId}
              newTopicPending={newTopicPending}
              onNewTopicToggle={() => setNewTopicPending((v) => !v)}
              streaming={streaming}
              onExport={handleExport}
              exportDisabled={!messages.length}
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
