import { memo, useCallback, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import LottiePlayer from "./LottiePlayer";
// 动画切换：改这里即可
//   dots-wave.json    — 三点波浪渐入渐出
//   dots-bounce.json  — 三点上下弹跳
//   dots-pulse.json   — 单圆脉冲呼吸
//   dots-typing.json  — 三点依次闪现（打字光标风）
//   dots-spin.json    — 圆环旋转
import thinkingAnim from "../../assets/dots-typing.json";
import { submitFeedback } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import type { ChatMessage, ToolTraceItem } from "../../api/types";
import { ToolTracePanel } from "./ToolTracePanel";

type Props = {
  message: ChatMessage;
  streaming?: boolean;
  hideModeTag?: boolean;
  liveTools?: ToolTraceItem[];
  sessionId?: string;
  questionForFeedback?: string;
};

function stripFootnotes(text: string): string {
  return text
    .replace(/\r?\n(\r?\n)?引用[:：][^\n]*(?:[;\n][^\n]*)*$/u, "")
    .trim();
}

function uniqueLabels(labels: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of labels) {
    const label = raw.trim();
    if (!label || seen.has(label)) continue;
    seen.add(label);
    out.push(label);
  }
  return out;
}

function sourceLabels(message: ChatMessage): string[] {
  const refs = message.meta?.source_refs;
  if (refs?.length) {
    return uniqueLabels(
      refs.map((r) => (r.source || "").split(/[/\\]/).pop() || r.source || r.parent_id || "")
    );
  }
  return uniqueLabels((message.meta?.sources || []).map((s) => s.split(/[/\\]/).pop() || s));
}

function resolveAnswerMode(message: ChatMessage): "kb" | "general" | null {
  const mode = message.meta?.answer_mode;
  if (mode === "kb" || mode === "general") return mode;
  if (message.role !== "assistant") return null;
  if (sourceLabels(message).length > 0) return "kb";
  if (message.content?.trim()) return "general";
  return null;
}

function MessageBubble({
  message,
  streaming,
  hideModeTag = false,
  liveTools,
  sessionId,
  questionForFeedback,
}: Props) {
  const { userId } = useAuth();
  const [feedback, setFeedback] = useState<number | null>(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correctionText, setCorrectionText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isUser = message.role === "user";
  const body = isUser ? message.content : stripFootnotes(message.content);
  const sources = sourceLabels(message);
  const answerMode = !isUser && !hideModeTag ? resolveAnswerMode(message) : null;
  const toolTrace = liveTools?.length ? liveTools : message.meta?.tool_trace;

  const sendFeedback = useCallback(
    async (rating: number, correction?: string) => {
      if (feedback !== null || submitting) return;
      setSubmitting(true);
      setFeedback(rating);
      setShowCorrection(false);
      try {
        await submitFeedback({
          user_id: userId,
          rating,
          trace_id: message.meta?.trace_id,
          message_id: message.meta?.trace_id,
          session_id: sessionId,
          question: questionForFeedback,
          answer_preview: body.slice(0, 500),
          answer_mode: answerMode ?? message.meta?.answer_mode,
          correction: correction?.trim() || undefined,
        });
      } catch {
        setFeedback(null);
      } finally {
        setSubmitting(false);
      }
    },
    [
      feedback,
      submitting,
      userId,
      message.meta?.trace_id,
      sessionId,
      questionForFeedback,
      body,
      answerMode,
      message.meta?.answer_mode,
    ]
  );

  const handleThumbsUp = useCallback(() => sendFeedback(1), [sendFeedback]);

  const handleThumbsDown = useCallback(() => {
    if (feedback !== null) return;
    setShowCorrection(true);
  }, [feedback]);

  const handleSubmitNegative = useCallback(() => {
    sendFeedback(0, correctionText);
    setCorrectionText("");
  }, [sendFeedback, correctionText]);

  const handleSkipNegative = useCallback(() => {
    setCorrectionText("");
    sendFeedback(0);
  }, [sendFeedback]);

  return (
    <div
      className={
        "flex gap-3 py-5 w-full max-w-[820px] mx-auto " +
        (isUser ? "justify-end" : "justify-start")
      }
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand to-brand-dark flex items-center justify-center text-xs text-white font-semibold shrink-0 mt-0.5">
          AI
        </div>
      )}

      <div className={isUser ? "max-w-[72%]" : "flex-1 min-w-0 max-w-[calc(100%-44px)]"}>
        {!isUser && answerMode && (
          <div className="mb-2">
            <span
              className={
                "inline-block text-[11px] font-semibold px-2.5 py-0.5 rounded-full " +
                (answerMode === "kb"
                  ? "bg-success-bg text-success"
                  : "bg-warning-bg text-warning")
              }
            >
              {answerMode === "kb" ? "知识库回答" : "通用回答"}
            </span>
          </div>
        )}

        {!isUser && toolTrace?.length ? (
          <ToolTracePanel items={toolTrace} live={Boolean(streaming && liveTools?.length)} />
        ) : null}

        <div
          className={
            "text-[15px] leading-relaxed " +
            (isUser
              ? "bg-brand text-white rounded-2xl rounded-br-md px-4 py-2.5 whitespace-pre-wrap break-words shadow-sm"
              : "text-text py-0.5 " + (streaming && body ? "after:content-['▋'] after:text-brand after:animate-pulse after:ml-0.5" : !streaming ? "markdown-body" : ""))
          }
        >
          {isUser ? (
            body
          ) : streaming && !body ? (
            <div className="flex items-center gap-1.5 py-1">
              <LottiePlayer
                animationData={JSON.stringify(thinkingAnim)}
                loop
                className="w-[72px] h-[20px]"
              />
              <span className="text-xs text-text-muted">思考中</span>
            </div>
          ) : (
            <ReactMarkdown
              remarkPlugins={[[remarkGfm, { singleTilde: false }]]}
              components={{
                del: ({ children }) => <span className="line-through">{children}</span>,
              }}
            >
              {body || "…"}
            </ReactMarkdown>
          )}
        </div>

        {!isUser && sources.length > 0 && (
          <div className="flex flex-wrap gap-x-2.5 gap-y-1.5 mt-3 pt-2.5 border-t border-border-light text-xs text-text-muted">
            <span className="text-text-muted shrink-0">引用</span>
            <span className="break-all">{sources.join(" · ")}</span>
          </div>
        )}

        {!isUser && !streaming && showCorrection && feedback === null && (
          <div className="mt-3 p-3 rounded-lg border border-border bg-surface-muted space-y-2">
            <p className="text-xs text-text-muted">哪里不对？可选填一句话，便于我们改进（可跳过）</p>
            <textarea
              className="w-full text-sm border border-border rounded-md px-2.5 py-2 bg-white resize-none"
              rows={2}
              maxLength={500}
              placeholder="例如：引用的制度已过期 / 答案与资料不符"
              value={correctionText}
              onChange={(e) => setCorrectionText(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSubmitNegative}
                disabled={submitting}
                className="text-xs px-2.5 py-1 rounded-md bg-brand text-white hover:bg-brand-dark cursor-pointer disabled:opacity-50"
              >
                提交反馈
              </button>
              <button
                type="button"
                onClick={handleSkipNegative}
                disabled={submitting}
                className="text-xs px-2.5 py-1 rounded-md bg-surface-muted text-text-muted hover:bg-border cursor-pointer disabled:opacity-50"
              >
                跳过
              </button>
              <button
                type="button"
                onClick={() => setShowCorrection(false)}
                className="text-xs px-2.5 py-1 rounded-md text-text-muted hover:text-text cursor-pointer"
              >
                取消
              </button>
            </div>
          </div>
        )}

        {!isUser && !streaming && (
          <div className="flex gap-1 mt-2 opacity-0 hover:opacity-100 transition-opacity group-focus-within:opacity-100">
            <button
              type="button"
              onClick={handleThumbsUp}
              disabled={feedback !== null || submitting}
              className={"text-xs px-2.5 py-1 rounded-md cursor-pointer " + (feedback === 1 ? "bg-success-bg text-success" : "bg-surface-muted text-text-muted hover:bg-border hover:text-text")}
              title="有帮助"
            >
              👍
            </button>
            <button
              type="button"
              onClick={handleThumbsDown}
              disabled={feedback !== null || submitting || showCorrection}
              className={"text-xs px-2.5 py-1 rounded-md cursor-pointer " + (feedback === 0 ? "bg-warning-bg text-warning" : "bg-surface-muted text-text-muted hover:bg-border hover:text-text")}
              title="没帮助"
            >
              👎
            </button>
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(body)}
              className="text-xs px-2.5 py-1 rounded-md bg-surface-muted text-text-muted hover:bg-border hover:text-text cursor-pointer"
            >
              复制
            </button>
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-surface-muted flex items-center justify-center text-xs text-text-muted font-semibold shrink-0 mt-0.5 order-1">
          你
        </div>
      )}
    </div>
  );
}

export default memo(MessageBubble);
