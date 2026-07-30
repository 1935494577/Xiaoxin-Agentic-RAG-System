import { type ReactNode, useState } from "react";
import { cn } from "../../lib/utils";

type Tab = { id: string; label: string; content: ReactNode };

type Props = {
  tabs: Tab[];
  defaultTab?: string;
  /** Controlled active tab id (sync with URL etc.). */
  activeTab?: string;
  onTabChange?: (id: string) => void;
  className?: string;
};

export function Tabs({ tabs, defaultTab, activeTab, onTabChange, className }: Props) {
  const [internal, setInternal] = useState(defaultTab || tabs[0]?.id || "");
  const controlled = activeTab !== undefined;
  const active = controlled ? activeTab! : internal;

  const select = (id: string) => {
    if (!controlled) setInternal(id);
    onTabChange?.(id);
  };

  return (
    <div className={className}>
      <div className="flex border-b border-border mb-4">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => select(t.id)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors cursor-pointer",
              active === t.id
                ? "border-brand text-brand"
                : "border-transparent text-text-muted hover:text-text"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div>{tabs.find((t) => t.id === active)?.content}</div>
    </div>
  );
}
