import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../api/client";
import "./MessageBubble.css";

type Props = {
  message: ChatMessage;
  userLabel?: string;
  streaming?: boolean;
  streamingMode?: "kb" | "general" | null;
};

function stripFootnotes(text: string): string {
  const idx = text.indexOf("\n\n引用:");
  return idx >= 0 ? text.slice(0, idx).trim() : text;
}

function sourceLabels(message: ChatMessage): string[] {
  const refs = message.meta?.source_refs;
  if (refs?.length) {
    return refs.map((r) => {
      const src = r.source || "";
      return src.split(/[/\\]/).pop() || src || r.parent_id || "";
    });
  }
  return (message.meta?.sources || []).map((s) => s.split(/[/\\]/).pop() || s);
}

function resolveAnswerMode(
  message: ChatMessage,
  streamingMode?: "kb" | "general" | null,
): "kb" | "general" | null {
  const mode = message.meta?.answer_mode || streamingMode;
  if (mode === "kb" || mode === "general") return mode;
  if (message.role !== "assistant") return null;
  if (sourceLabels(message).length > 0) return "kb";
  if (message.content?.trim()) return "general";
  return null;
}

export default function MessageBubble({
  message,
  userLabel = "你",
  streaming,
  streamingMode,
}: Props) {
  const isUser = message.role === "user";
  const body = isUser ? message.content : stripFootnotes(message.content);
  const sources = sourceLabels(message);
  const answerMode = !isUser ? resolveAnswerMode(message, streamingMode) : null;

  return (
    <div className={"message-row" + (isUser ? " user" : " assistant")}>
      {!isUser && <div className="avatar bot">AI</div>}
      <div className="bubble">
        {!isUser && answerMode && (
          <div className="mode-tag-row">
            <span className={"mode-tag " + answerMode}>
              {answerMode === "kb" ? "知识库回答" : "通用回答"}
            </span>
          </div>
        )}
        <div className={"content" + (streaming ? " streaming-cursor" : "")}>
          {isUser ? (
            body
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{body || (streaming ? "" : "…")}</ReactMarkdown>
          )}
        </div>
        {!isUser && sources.length > 0 && (
          <div className="sources-row">
            <span className="sources-label">引用</span>
            <span className="sources-list">{sources.join(" · ")}</span>
          </div>
        )}
        {!isUser && !streaming && (
          <div className="actions">
            <button type="button" onClick={() => navigator.clipboard.writeText(body)}>
              复制
            </button>
          </div>
        )}
      </div>
      {isUser && <div className="avatar user">{userLabel[0]}</div>}
    </div>
  );
}
