import { MessageSquarePlus, Info, Download } from "lucide-react";
import { AssistantModeSwitcher } from "./AssistantModeSwitcher";
import { ThreadTokenBadge } from "./ThreadTokenBadge";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import type { AssistantMode } from "@/lib/assistantMode";

type Props = {
  assistantMode: AssistantMode;
  onAssistantModeChange: (mode: AssistantMode) => void;
  department?: string;
  sessionId?: string | null;
  newTopicPending: boolean;
  onNewTopicToggle: () => void;
  streaming: boolean;
  onExport?: () => void;
  exportDisabled?: boolean;
};

export function ChatToolbar({
  assistantMode,
  onAssistantModeChange,
  department,
  sessionId,
  newTopicPending,
  onNewTopicToggle,
  streaming,
  onExport,
  exportDisabled,
}: Props) {
  return (
    <div className="max-w-[768px] mx-auto space-y-2">
      <div className="flex items-center gap-3 flex-wrap rounded-xl border border-border bg-surface-muted/50 px-3 py-2">
        <AssistantModeSwitcher
          value={assistantMode}
          onChange={onAssistantModeChange}
          disabled={streaming}
        />
        {department ? (
          <>
            <span className="hidden sm:inline h-4 w-px bg-border" aria-hidden />
            <span
              className="text-[11px] text-text-muted px-2 py-0.5 rounded-full bg-surface border border-border"
              title="检索权限按登录部门过滤；与同事不一致时回答可能不同"
            >
              部门：{department}
            </span>
          </>
        ) : null}
        <ThreadTokenBadge threadId={sessionId} />
        <span className="hidden sm:inline h-4 w-px bg-border" aria-hidden />
        <button
          type="button"
          disabled={streaming}
          onClick={onNewTopicToggle}
          title="下一条消息将忽略此前对话与知识库语境，适合在同一窗口切换话题"
          className={
            "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed " +
            (newTopicPending
              ? "border-brand bg-brand-light text-brand"
              : "border-border bg-surface text-text-muted hover:border-brand hover:text-brand")
          }
        >
          <MessageSquarePlus size={14} />
          {newTopicPending ? "下一条：新话题" : "新话题"}
        </button>
        {onExport ? (
          <>
            <span className="hidden sm:inline h-4 w-px bg-border" aria-hidden />
            <button
              type="button"
              disabled={streaming || exportDisabled}
              onClick={onExport}
              title="导出当前对话为 Markdown"
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-muted hover:border-brand hover:text-brand transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download size={14} />
              导出
            </button>
          </>
        ) : null}
        <span className="ml-auto">
          <ThemeToggle />
        </span>
      </div>
      {newTopicPending && (
        <p className="flex items-start gap-1.5 text-xs text-brand px-1">
          <Info size={14} className="shrink-0 mt-0.5" />
          已开启：发送后将不带历史上下文，并清空会话滚动摘要。
        </p>
      )}
    </div>
  );
}
