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
      <div className="flex gap-1 border-b border-border mb-5 px-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => select(t.id)}
            className={cn(
              "relative px-4 py-2.5 text-sm font-medium transition-colors duration-200 cursor-pointer rounded-t-lg",
              active === t.id
                ? "text-brand bg-surface-muted/50"
                : "text-text-muted hover:text-text hover:bg-surface-muted/40"
            )}
          >
            {t.label}
            <span
              className={cn(
                "absolute bottom-0 left-1/2 h-0.5 bg-brand rounded-full transition-all duration-200",
                active === t.id ? "w-full -translate-x-1/2" : "w-0 -translate-x-1/2"
              )}
            />
          </button>
        ))}
      </div>
      <div>{tabs.find((t) => t.id === active)?.content}</div>
    </div>
  );
}
