import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchUiConfig } from "../api/client";
import { HYBRID_MODE_KEY } from "../lib/constants";
import { useAuth } from "../hooks/useAuth";
import { useSessions, useMessages } from "../hooks/useSessions";
import { useChatStream } from "../hooks/useChatStream";
import { useLocalStorage } from "../hooks/useLocalStorage";
import type { ChatMessage } from "../api/types";
import { ChatInput } from "../components/chat/ChatInput";
import { SessionList } from "../components/chat/SessionList";
import { HybridToggle } from "../components/chat/HybridToggle";
import MessageBubble from "../components/chat/MessageBubble";

const SUGGESTIONS_FALLBACK = [
  "1-3年级超脑阅读要求是什么？",
  "把文档放进知识库后如何提问？",
  "支持哪些文件格式入库？",
];

export default function ChatPage() {
  const { userId } = useAuth();
  const { sessions, create, remove } = useSessions(userId);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const { data: messages = [], refetch: refetchMessages } = useMessages(userId, sessionId);
  const { data: uiConfig } = useQuery({
    queryKey: ["uiConfig"],
    queryFn: fetchUiConfig,
    staleTime: 300_000,
  });

  const [input, setInput] = useState("");
  const [department, setDepartment] = useState("技术");
  const [hybridExpert, setHybridExpert] = useLocalStorage<boolean>(HYBRID_MODE_KEY, false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const initDone = useRef(false);
  const [displayMessages, setDisplayMessages] = useState<ChatMessage[]>([]);

  const persisted = useCallback(() => {
    refetchMessages();
  }, [refetchMessages]);

  const { streaming, streamText, error, send, abort } = useChatStream(userId, persisted);

  // Init: pick first session
  useEffect(() => {
    if (initDone.current) return;
    if (sessions.length && !sessionId) {
      const first = sessions.find((s) => s.id) || sessions[0];
      setSessionId(first.id);
      initDone.current = true;
    }
  }, [sessions, sessionId]);

  // Apply uiConfig hybrid mode default on first load
  useEffect(() => {
    if (initDone.current) return;
    if (uiConfig && typeof uiConfig.hybrid_expert_mode === "boolean") {
      const stored = localStorage.getItem(HYBRID_MODE_KEY);
      if (stored === null) {
        setHybridExpert(uiConfig.hybrid_expert_mode);
      }
    }
  }, [uiConfig, setHybridExpert]);

  // Sync messages for display (append streaming token)
  useEffect(() => {
    if (streaming && streamText) {
      const streamingMsg: ChatMessage = { role: "assistant", content: streamText };
      setDisplayMessages([...messages, streamingMsg]);
    } else {
      setDisplayMessages(messages);
    }
  }, [messages, streaming, streamText]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayMessages, streamText, streaming]);

  const handleNew = async () => {
    const s = await create();
    setSessionId(s.id);
  };

  const handleDelete = async () => {
    if (!sessionId || !confirm("确认删除此对话？")) return;
    await remove(sessionId);
    setSessionId(null);
    initDone.current = false;
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");

    let sid = sessionId;
    if (!sid) {
      const s = await create();
      sid = s.id;
      setSessionId(sid);
    }

    const updated = await send(
      {
        message: text,
        user_id: userId,
        session_id: sid,
        user_department: department,
        hybrid_expert_mode: hybridExpert,
      },
      messages
    );
    setDisplayMessages(updated);
  };

  const suggestedQuestions = uiConfig?.suggested_questions?.filter((q) => String(q).trim()).slice(0, 12) || SUGGESTIONS_FALLBACK;
  const inputPlaceholder = hybridExpert
    ? "输入问题；优先知识库，必要时补充通用能力"
    : "输入问题，助手将基于知识库内容回答";

  return (
    <div className="flex h-full">
      <SessionList
        sessions={sessions}
        activeId={sessionId}
        onSelect={(id) => {
          setSessionId(id);
          setDisplayMessages([]);
        }}
        onNew={handleNew}
        onDelete={handleDelete}
        department={department}
        onDepartment={setDepartment}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Error banner */}
        {error && (
          <div className="bg-error-bg text-error text-sm text-center py-2">{error}</div>
        )}

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto bg-surface-muted px-5 pb-4">
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

            {displayMessages.map((m, i) => (
              <MessageBubble
                key={m.id || i}
                message={m}
                hideModeTag
                streaming={streaming && i === displayMessages.length - 1 && m.role === "assistant"}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-border bg-white px-5 pt-3 pb-5">
          <div className="max-w-[820px] mx-auto mb-2.5 flex items-center gap-3 flex-wrap">
            <HybridToggle enabled={hybridExpert} onChange={setHybridExpert} disabled={streaming} />
          </div>
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={handleSend}
            streaming={streaming}
            onStop={abort}
            placeholder={inputPlaceholder}
          />
          <p className="max-w-[820px] mx-auto mt-2 text-xs text-center text-text-muted">
            Enter 发送 · Shift+Enter 换行
          </p>
        </div>
      </div>
    </div>
  );
}
