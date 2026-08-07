import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight, Lightbulb } from "lucide-react";
import type { HelpStep } from "../../lib/adminHelp";

type Props = {
  title?: string;
  summary: string;
  steps?: HelpStep[];
  tips?: string[];
  defaultOpen?: boolean;
  children?: ReactNode;
};

export function SectionGuide({
  title = "怎么用",
  summary,
  steps,
  tips,
  defaultOpen = true,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="mb-6 rounded-xl border border-brand/20 bg-brand-light/25 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-2 px-4 py-3 text-left hover:bg-brand-light/40 transition-colors cursor-pointer border-none bg-transparent"
      >
        <Lightbulb size={18} className="text-brand shrink-0 mt-0.5" aria-hidden />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-text">{title}</span>
            {open ? (
              <ChevronDown size={16} className="text-text-muted" />
            ) : (
              <ChevronRight size={16} className="text-text-muted" />
            )}
          </div>
          <p className="text-xs text-text-muted mt-1 leading-relaxed">{summary}</p>
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-0 border-t border-brand/10 space-y-4">
          {steps && steps.length > 0 && (
            <ol className="grid grid-cols-1 sm:grid-cols-2 gap-3 list-none m-0 p-0">
              {steps.map((step, i) => (
                <li
                  key={step.title}
                  className="rounded-lg bg-surface/80 border border-border px-3 py-2.5 text-sm"
                >
                  <span className="font-medium text-text">
                    {i + 1}. {step.title}
                  </span>
                  <p className="text-xs text-text-muted mt-1 leading-relaxed">{step.detail}</p>
                </li>
              ))}
            </ol>
          )}
          {tips && tips.length > 0 && (
            <ul className="text-xs text-text-muted space-y-1 list-disc pl-5 m-0">
              {tips.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          )}
          {children}
        </div>
      )}
    </section>
  );
}

/** 工具栏分组：筛选 / 操作 / 其他 */
export function ToolbarSection({
  label,
  children,
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <span className="text-xs font-medium text-text-muted uppercase tracking-wide mr-1">{label}</span>
      {children}
    </div>
  );
}
