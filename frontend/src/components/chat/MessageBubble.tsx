import { memo, useCallback, useRef, useState } from "react";
import { Check, Copy, FileText, ThumbsDown, ThumbsUp } from "lucide-react";
import LottiePlayer from "./LottiePlayer";
import thinkingAnim from "../../assets/dots-typing.json";
import { submitFeedback } from "../../api/client";
import { useAuth } from "../../hooks/useAuth";
import type { ChatMessage, GraphViz } from "../../api/types";
import { MarkdownContent, StreamingPlainText } from "./MarkdownContent";
import { ChatAvatar } from "./ChatAvatar";
import { SourcePreviewButton } from "./SourcePreviewButton";
import RelationshipGraphView from "./RelationshipGraphView";
import { ExamPaperCard } from "./ExamPaperCard";
import { ExamCandidateList } from "./ExamCandidateList";
import { graphVizFromMessageMeta } from "../../lib/graphViz";
import {
  collectExamCandidateBlocks,
  collectExamPaperBlocks,
  stripExamPaperFences,
} from "../../lib/examPaperBlocks";

type Props = {
  message: ChatMessage;
  streaming?: boolean;
  hideModeTag?: boolean;
  sessionId?: string;
  questionForFeedback?: string;
  userAvatar?: string;
  userDisplayName?: string;
  aiAvatar?: string;
  aiDisplayName?: string;
  userDepartment?: string;
  graphViz?: GraphViz | null;
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
  sessionId,
  questionForFeedback,
  userAvatar = "",
  userDisplayName = "",
  aiAvatar = "",
  aiDisplayName = "",
  userDepartment = "技术部",
  graphViz: graphVizProp,
}: Props) {
  const { userId } = useAuth();
  const [feedback, setFeedback] = useState<number | null>(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correctionText, setCorrectionText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [copied, setCopied] = useState(false);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isUser = message.role === "user";
  const rawBody = isUser ? message.content : stripFootnotes(message.content);
  const examBlocks = !isUser
    ? collectExamPaperBlocks(rawBody, message.meta?.ui_blocks)
    : [];
  const candidateBlocks = !isUser
    ? collectExamCandidateBlocks(rawBody, message.meta?.ui_blocks)
    : [];
  const body =
    !isUser && (examBlocks.length || candidateBlocks.length)
      ? stripExamPaperFences(rawBody)
      : rawBody;
  const sources = sourceLabels(message);
  const answerMode = !isUser && !hideModeTag ? resolveAnswerMode(message) : null;
  const graphViz = graphVizProp ?? graphVizFromMessageMeta(message.meta);

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

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(body).then(() => {
      setCopied(true);
      if (copiedTimer.current) clearTimeout(copiedTimer.current);
      copiedTimer.current = setTimeout(() => setCopied(false), 1500);
    }).catch(() => {
      /* clipboard 不可用时静默 */
    });
  }, [body]);

  return (
    <div
      className={
        "group flex gap-4 py-4 w-full max-w-[768px] mx-auto " +
        (isUser ? "justify-end" : "justify-start")
      }
    >
      {!isUser && (
        <ChatAvatar
          avatarUrl={aiAvatar}
          label={aiDisplayName}
          fallback="AI"
          variant="ai"
          size="chat"
        />
      )}

      <div className={isUser ? "max-w-[85%] sm:max-w-[72%]" : "flex-1 min-w-0"}>
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

        {isUser ? (
          <div className="text-[15px] leading-relaxed bg-brand text-white rounded-2xl rounded-br-md px-4 py-2.5 whitespace-pre-wrap break-words shadow-sm">
            {body}
          </div>
        ) : (
          <div className="assistant-answer">
            {streaming && !body ? (
              <div className="flex items-center gap-1.5 py-1">
                <LottiePlayer
                  animationData={JSON.stringify(thinkingAnim)}
                  loop
                  className="w-[72px] h-[20px]"
                />
                <span className="text-xs text-text-muted">思考中</span>
              </div>
            ) : streaming ? (
              <StreamingPlainText content={body} />
            ) : body ? (
              <MarkdownContent content={body} />
            ) : examBlocks.length || candidateBlocks.length ? null : (
              <p className="text-text-muted text-sm">…</p>
            )}
            {!streaming &&
              candidateBlocks.map((block, i) => (
                <ExamCandidateList key={`cand-${i}`} items={block.items} />
              ))}
            {!streaming &&
              examBlocks.map((b) => (
                <ExamPaperCard
                  key={b.source_paper_id}
                  sourcePaperId={b.source_paper_id}
                  titleHint={b.title}
                />
              ))}
          </div>
        )}

        {!isUser && graphViz && <RelationshipGraphView graph={graphViz} />}

        {!isUser && sources.length > 0 && (
          <div className="mt-4 pt-3 border-t border-border-light">
            <p className="mb-2 text-xs font-medium text-text-muted">引用来源</p>
            <div className="flex flex-wrap gap-1.5 text-xs">
              {message.meta?.source_refs?.length ? (
                message.meta.source_refs.map((ref, idx) => {
                  const label =
                    (ref.source || "").split(/[/\\]/).pop() || ref.source || ref.parent_id || `来源${idx + 1}`;
                  if (ref.parent_id) {
                    return (
                      <SourcePreviewButton
                        key={`${ref.parent_id}-${idx}`}
                        parentId={ref.parent_id}
                        label={label}
                        department={userDepartment}
                      />
                    );
                  }
                  return (
                    <span
                      key={`${label}-${idx}`}
                      className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-border bg-surface-muted px-2.5 py-1 text-text-muted"
                    >
                      <FileText className="h-3.5 w-3.5 shrink-0" aria-hidden />
                      <span className="truncate">{label}</span>
                    </span>
                  );
                })
              ) : (
                sources.map((label, idx) => (
                  <span
                    key={`${label}-${idx}`}
                    className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-border bg-surface-muted px-2.5 py-1 text-text-muted"
                  >
                    <FileText className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    <span className="truncate">{label}</span>
                  </span>
                ))
              )}
            </div>
          </div>
        )}

        {!isUser && !streaming && showCorrection && feedback === null && (
          <div className="mt-3 p-3 rounded-lg border border-border bg-surface-muted space-y-2">
            <p className="text-xs text-text-muted">哪里不对？可选填一句话，便于我们改进（可跳过）</p>
            <textarea
              className="w-full text-sm border border-border rounded-md px-2.5 py-2 bg-surface resize-none"
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
          <div className="flex items-center gap-1 mt-2.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
            <button
              type="button"
              onClick={handleThumbsUp}
              disabled={feedback !== null || submitting}
              aria-label="有帮助"
              className={
                "inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md cursor-pointer transition-colors disabled:opacity-60 " +
                (feedback === 1
                  ? "bg-success-bg text-success"
                  : "text-text-muted hover:bg-surface-muted hover:text-text")
              }
            >
              <ThumbsUp className="h-3.5 w-3.5" aria-hidden />
            </button>
            <button
              type="button"
              onClick={handleThumbsDown}
              disabled={feedback !== null || submitting || showCorrection}
              aria-label="没帮助"
              className={
                "inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md cursor-pointer transition-colors disabled:opacity-60 " +
                (feedback === 0
                  ? "bg-warning-bg text-warning"
                  : "text-text-muted hover:bg-surface-muted hover:text-text")
              }
            >
              <ThumbsDown className="h-3.5 w-3.5" aria-hidden />
            </button>
            <button
              type="button"
              onClick={handleCopy}
              aria-label="复制回答"
              className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md cursor-pointer transition-colors text-text-muted hover:bg-surface-muted hover:text-text"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-success" aria-hidden />
              ) : (
                <Copy className="h-3.5 w-3.5" aria-hidden />
              )}
              {copied ? "已复制" : "复制"}
            </button>
          </div>
        )}
      </div>

      {isUser && (
        <ChatAvatar
          avatarUrl={userAvatar}
          label={userDisplayName}
          fallback="你"
          variant="user"
          size="chat"
        />
      )}
    </div>
  );
}

export default memo(MessageBubble, (prev, next) => {
  if (prev.streaming || next.streaming) return false;
  const prevGraph = prev.graphViz ?? graphVizFromMessageMeta(prev.message.meta);
  const nextGraph = next.graphViz ?? graphVizFromMessageMeta(next.message.meta);
  if (prevGraph !== nextGraph) return false;
  const prevBlocks = prev.message.meta?.ui_blocks;
  const nextBlocks = next.message.meta?.ui_blocks;
  if (prevBlocks !== nextBlocks) return false;
  return (
    prev.message.content === next.message.content &&
    prev.message.role === next.message.role &&
    prev.hideModeTag === next.hideModeTag &&
    prev.sessionId === next.sessionId &&
    prev.questionForFeedback === next.questionForFeedback &&
    prev.userAvatar === next.userAvatar &&
    prev.userDisplayName === next.userDisplayName &&
    prev.aiAvatar === next.aiAvatar &&
    prev.aiDisplayName === next.aiDisplayName
  );
});
