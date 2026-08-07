import { MessageSquarePlus } from "lucide-react";
import type { ChatSession } from "../../api/types";
import { groupSessionsByDate } from "../../lib/sessionGroups";

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
            className="flex-1 cursor-pointer rounded-lg border border-border bg-surface px-3 py-2 text-sm transition-colors hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
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
          groupSessionsByDate(sessions).map((group) => (
            <div key={group.key} className="mb-2">
              <p className="px-3 pb-1 pt-2 text-[11px] font-medium tracking-wide text-text-muted/70">
                {group.label}
              </p>
              {group.items.map((s) => {
                const active = s.id === activeId;
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => onSelect(s.id)}
                    className={
                      "relative mb-0.5 w-full cursor-pointer truncate rounded-lg px-3 py-2.5 text-left text-sm transition-colors " +
                      (active
                        ? "bg-brand-light font-medium text-brand"
                        : "text-text hover:bg-surface/70")
                    }
                    title={s.title}
                  >
                    {active ? (
                      <span
                        aria-hidden
                        className="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-full bg-brand"
                      />
                    ) : null}
                    {s.title || "新对话"}
                  </button>
                );
              })}
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
