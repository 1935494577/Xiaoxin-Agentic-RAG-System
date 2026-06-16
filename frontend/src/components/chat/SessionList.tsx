import { MessageSquarePlus } from "lucide-react";
import type { ChatSession } from "../../api/types";

type Props = {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: () => void;
};

export function SessionList({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  return (
    <aside className="flex h-full w-[260px] shrink-0 flex-col border-r border-border bg-surface-muted">
      <div className="border-b border-border p-4">
        <h2 className="mb-1 text-sm font-semibold text-text">对话列表</h2>
        <p className="mb-3 text-xs text-text-muted">按会话保存上下文与摘要</p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onNew}
            className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-dark"
          >
            <MessageSquarePlus className="h-4 w-4" aria-hidden />
            新建
          </button>
          <button
            type="button"
            onClick={onDelete}
            disabled={!activeId}
            className="flex-1 cursor-pointer rounded-lg border border-border bg-white px-3 py-2 text-sm transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
          >
            删除
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {sessions.length === 0 ? (
          <div className="px-3 py-10 text-center">
            <p className="text-sm text-text-muted">暂无对话</p>
            <p className="mt-1 text-xs leading-relaxed text-text-muted/80">
              点击「新建」开始第一次提问
            </p>
          </div>
        ) : (
          sessions.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => onSelect(s.id)}
              className={
                "mb-1 w-full cursor-pointer truncate rounded-lg px-3 py-2.5 text-left text-sm transition-colors " +
                (s.id === activeId
                  ? "bg-brand-light font-medium text-brand"
                  : "text-text hover:bg-white/70")
              }
              title={s.title}
            >
              {s.title || "新对话"}
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
