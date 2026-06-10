import type { ChatSession } from "../api/client";
import "./Sidebar.css";

type Props = {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: () => void;
  department: string;
  onDepartment: (d: string) => void;
};

const DEPTS = ["general", "技术", "市场", "人事", "财务"];

export default function Sidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDelete,
  department,
  onDepartment,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>Jnao Chat</h1>
        <div className="sidebar-actions">
          <button type="button" className="primary" onClick={onNew}>
            新建
          </button>
          <button type="button" onClick={onDelete} disabled={!activeId}>
            删除
          </button>
        </div>
      </div>
      <div className="session-list">
        {sessions.map((s) => (
          <button
            key={s.id}
            type="button"
            className={"session-item" + (s.id === activeId ? " active" : "")}
            onClick={() => onSelect(s.id)}
            title={s.title}
          >
            {s.title || "新对话"}
          </button>
        ))}
      </div>
      <div className="sidebar-footer">
        <div>部门权限</div>
        <select value={department} onChange={(e) => onDepartment(e.target.value)}>
          {DEPTS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>
    </aside>
  );
}
