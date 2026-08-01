import { useCallback, useRef, useState } from "react";
import { appendMessages, createSession, streamChat } from "../api/client";
import { resolveStreamFastMode } from "../lib/chatDefaults";
import type {
  ChatMessage,
  ClarifyOption,
  GraphViz,
  StreamEvent,
  ToolTraceItem,
  UiConfig,
} from "../api/types";
import type { AssistantMode } from "../lib/assistantMode";
import { type ExecutionStep } from "../lib/executionTimeline";
import { reduceStreamTurnEvent } from "../lib/chatStreamTurn";

export type ClarifyPending = {
  message: string;
  prompt: string;
  options: ClarifyOption[];
  sessionId: string;
};

type UseChatTurnArgs = {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  assistantMode: AssistantMode;
  uiConfig: UiConfig | undefined;
  newTopicPending: boolean;
  setNewTopicPending: (v: boolean) => void;
  refreshSessions: () => Promise<unknown>;
};

export function useChatTurn({
  sessionId,
  setSessionId,
  messages,
  setMessages,
  assistantMode,
  uiConfig,
  newTopicPending,
  setNewTopicPending,
  refreshSessions,
}: UseChatTurnArgs) {
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [, setStreamExecutionSteps] = useState<ExecutionStep[]>([]);
  const [streamGraphViz, setStreamGraphViz] = useState<GraphViz | null>(null);
  const [error, setError] = useState("");
  const [clarifyPending, setClarifyPending] = useState<ClarifyPending | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const runChatTurn = useCallback(
    async (
      text: string,
      opts?: { clarifyChoiceId?: string; appendUser?: boolean; sessionId?: string },
    ) => {
      if (streaming) return;

      setError("");
      setClarifyPending(null);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      let sid = opts?.sessionId || sessionId;
      if (!sid) {
        const s = await createSession();
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
      const turnState = {
        clarifyEvt: null as Extract<StreamEvent, { type: "clarify" }> | null,
        needsClarify: false,
      };
      const priorHistory = newTopicPending
        ? []
        : messages.map((m) => ({ role: m.role, content: m.content }));
      const resetContext = newTopicPending;

      try {
        await streamChat(
          {
            message: text,
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
                needsClarify: turnState.needsClarify,
                clarifyEvt: turnState.clarifyEvt,
              },
              evt,
              assistantMode,
            );
            assistant = acc.assistant;
            streamError = acc.streamError;
            meta = acc.meta;
            toolTrace = acc.toolTrace;
            executionSteps = acc.executionSteps;
            graphViz = acc.graphViz;
            turnState.needsClarify = acc.needsClarify;
            turnState.clarifyEvt = acc.clarifyEvt;

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
          ctrl.signal,
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

      if (ctrl.signal.aborted) {
        const stopped = assistant.trim()
          ? `${assistant.trim()}\n\n（已停止生成）`
          : "（已停止生成）";
        setMessages((prev) => [...prev, { role: "assistant", content: stopped, meta }]);
        return;
      }

      if (turnState.clarifyEvt) {
        setClarifyPending({
          message: text,
          prompt: turnState.clarifyEvt.prompt,
          options: turnState.clarifyEvt.options,
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
        await appendMessages(sid!, toPersist, text);
        await refreshSessions();
      } catch (err) {
        console.error("消息持久化失败", err);
      }
    },
    [
      assistantMode,
      messages,
      newTopicPending,
      refreshSessions,
      sessionId,
      setMessages,
      setNewTopicPending,
      setSessionId,
      streaming,
      uiConfig,
    ],
  );

  const handleClarifyPick = useCallback(
    async (choiceId: string) => {
      if (!clarifyPending || streaming) return;
      const { message, sessionId: sid } = clarifyPending;
      setClarifyPending(null);
      await runChatTurn(message, {
        clarifyChoiceId: choiceId,
        appendUser: false,
        sessionId: sid,
      });
    },
    [clarifyPending, runChatTurn, streaming],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    streaming,
    streamText,
    streamGraphViz,
    error,
    setError,
    clarifyPending,
    runChatTurn,
    handleClarifyPick,
    abort,
  };
}
