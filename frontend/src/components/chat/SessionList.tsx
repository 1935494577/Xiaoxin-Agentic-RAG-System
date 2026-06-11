import type { ChatSession } from "../../api/types";
import { DEPT_OPTIONS } from "../../lib/constants";

type Props = {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: () => void;
  department: string;
  onDepartment: (d: string) => void;
};

export function SessionList({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDelete,
  department,
  onDepartment,
}: Props) {
  return (
    <aside className="w-[260px] bg-surface-muted border-r border-border flex flex-col shrink-0">
      <div className="p-4 border-b border-border">
        <h2 className="text-base font-semibold mb-3">Jnao Chat</h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onNew}
            className="flex-1 py-2 px-3 rounded-lg bg-brand text-white text-sm font-medium cursor-pointer hover:bg-brand-dark transition-colors"
          >
            新建
          </button>
          <button
            type="button"
            onClick={onDelete}
            disabled={!activeId}
            className="flex-1 py-2 px-3 rounded-lg bg-white border border-border text-sm cursor-pointer hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            删除
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {sessions.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect(s.id)}
            className={
              "w-full text-left px-3 py-2.5 rounded-lg text-sm mb-1 truncate transition-colors cursor-pointer " +
              (s.id === activeId ? "bg-brand-light text-brand font-medium" : "text-text hover:bg-surface-muted/80")
            }
            title={s.title}
          >
            {s.title || "新对话"}
          </button>
        ))}
      </div>

      <div className="p-3 border-t border-border text-xs text-text-muted">
        <div className="mb-1">部门权限</div>
        <select
          value={department}
          onChange={(e) => onDepartment(e.target.value)}
          className="w-full rounded-lg border border-border bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
        >
          {DEPT_OPTIONS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>
    </aside>
  );
}
