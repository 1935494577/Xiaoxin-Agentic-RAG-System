import { useLocation } from "react-router-dom";
import { NavLink } from "react-router-dom";
import { MessageSquare, Database, Wrench, HardDrive, Brain, FileText, Cpu, Activity, BookOpen, ThumbsUp } from "lucide-react";

const NAV_ITEMS = [
  { id: "chat", label: "Jnao Chat", href: "/", icon: MessageSquare, primary: true },
  { id: "ingest", label: "数据入库", href: "/admin/ingest", icon: Database },
  { id: "processing", label: "工具", href: "/admin/processing", icon: Wrench },
  { id: "vector_store", label: "向量库", href: "/admin/vector-store", icon: HardDrive },
  { id: "memory", label: "对话记忆", href: "/admin/memory", icon: Brain },
  { id: "prompts", label: "提示词", href: "/admin/prompts", icon: FileText },
  { id: "models", label: "模型", href: "/admin/models", icon: Cpu },
  { id: "feedback", label: "用户反馈", href: "/admin/feedback", icon: ThumbsUp },
  { id: "trace", label: "链路 Trace", href: "/admin/trace", icon: Activity },
  { id: "tutorial", label: "教程", href: "/admin/tutorial", icon: BookOpen },
];

export function Sidebar() {
  const location = useLocation();

  const isActive = (href: string) => {
    if (href === "/") return location.pathname === "/";
    return location.pathname.startsWith(href);
  };

  return (
    <aside className="w-[240px] bg-surface-muted border-r border-border flex flex-col shrink-0">
      <div className="px-4 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <img src="/company_logo.png" alt="Logo" className="h-7 w-auto" />
          <h1 className="text-base font-semibold text-brand">知识库</h1>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto p-2 flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;
          return (
            <NavLink
              key={item.id}
              to={item.href}
              className={
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors " +
                (active
                  ? "bg-brand-light text-brand font-semibold"
                  : "text-text-muted hover:bg-surface-muted/80 hover:text-text")
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="truncate">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="px-4 py-3 border-t border-border text-xs text-text-muted">
        Enterprise RAG
      </div>
    </aside>
  );
}
