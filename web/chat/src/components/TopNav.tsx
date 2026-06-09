import type { NavConfig } from "../api/client";
import "./TopNav.css";

type Props = {
  nav: NavConfig;
  activeId?: string;
};

export default function TopNav({ nav, activeId = "chat" }: Props) {
  return (
    <header className="unified-nav">
      <div className="unified-nav-brand">企业知识库</div>
      <nav className="unified-nav-links">
        {(nav.items || []).map((item) => {
          const active = item.id === activeId;
          const cls = active ? "unified-nav-link active" : "unified-nav-link";
          const admin = item.id !== "chat";
          return (
            <a
              key={item.id}
              className={cls + (admin ? " admin" : "")}
              href={item.href}
              target="_self"
            >
              {item.label}
            </a>
          );
        })}
      </nav>
      <span className="unified-nav-right">对话 · 管理同一浏览器切换</span>
    </header>
  );
}
