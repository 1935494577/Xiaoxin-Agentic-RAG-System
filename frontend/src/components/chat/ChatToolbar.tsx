import { MessageSquarePlus, Info } from "lucide-react";
import { HybridToggle } from "./HybridToggle";

type Props = {
  hybridExpert: boolean;
  onHybridChange: (on: boolean) => void;
  newTopicPending: boolean;
  onNewTopicToggle: () => void;
  streaming: boolean;
};

export function ChatToolbar({
  hybridExpert,
  onHybridChange,
  newTopicPending,
  onNewTopicToggle,
  streaming,
}: Props) {
  return (
    <div className="max-w-[768px] mx-auto space-y-2">
      <div className="flex items-center gap-3 flex-wrap rounded-xl border border-border bg-surface-muted/50 px-3 py-2">
        <HybridToggle enabled={hybridExpert} onChange={onHybridChange} disabled={streaming} />
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
              : "border-border bg-white text-text-muted hover:border-brand hover:text-brand")
          }
        >
          <MessageSquarePlus size={14} />
          {newTopicPending ? "下一条：新话题" : "新话题"}
        </button>
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
