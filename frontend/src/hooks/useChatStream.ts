import { useCallback, useRef, useState } from "react";
import { appendMessages, streamChat } from "../api/client";
import type { ChatMessage, StreamEvent, StreamPayload } from "../api/types";

type StreamState = {
  streaming: boolean;
  streamText: string;
  error: string;
};

export function useChatStream(userId: string, onPersist: () => void) {
  const [state, setState] = useState<StreamState>({
    streaming: false,
    streamText: "",
    error: "",
  });
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (payload: StreamPayload, priorMessages: ChatMessage[]) => {
      setState({ streaming: true, streamText: "", error: "" });

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      let assistant = "";
      let meta: ChatMessage["meta"] = {};

      await streamChat(
        {
          ...payload,
          user_id: userId,
          skip_query_rewrite: true,
          history: priorMessages.map((m) => ({ role: m.role, content: m.content })),
        },
        (evt: StreamEvent) => {
          if (evt.type === "token") {
            assistant += evt.content;
            setState((s) => ({ ...s, streamText: assistant }));
          } else if (evt.type === "error") {
            setState((s) => ({ ...s, error: evt.message }));
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
        ctrl.signal
      );

      setState({ streaming: false, streamText: "", error: "" });
      abortRef.current = null;

      const finalContent = assistant || state.error || "（无回复）";
      const userMsg: ChatMessage = { role: "user", content: payload.message };
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: finalContent,
        meta,
      };

      const all = [...priorMessages, userMsg, assistantMsg];
      try {
        if (payload.session_id) {
          await appendMessages(userId, payload.session_id, [userMsg, assistantMsg], payload.message);
          onPersist();
        }
      } catch {
        /* ignore persist errors */
      }

      return all;
    },
    [userId, onPersist]
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { ...state, send, abort };
}
