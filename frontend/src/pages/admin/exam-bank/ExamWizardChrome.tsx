import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { INGEST_STEPS } from "../../../lib/examWizardStore";

/** Unified labeled control for exam wizard forms */
export function ExamField({
  label,
  children,
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`block space-y-1.5 text-left ${className}`}>
      <span className="text-xs font-medium text-text-muted">{label}</span>
      {children}
    </label>
  );
}

export const examControlClass =
  "w-full rounded-lg border-2 border-border bg-surface px-3 py-2.5 text-sm text-text shadow-sm outline-none transition-colors focus:border-brand focus:ring-1 focus:ring-brand/30";

export function ExamWizardChrome({
  title,
  step,
  children,
  backTo = "/admin/exam-bank",
  wide = false,
}: {
  title: string;
  step?: number;
  children: ReactNode;
  backTo?: string;
  /** wide: 组卷等大屏；默认入库向导 */
  wide?: boolean;
}) {
  return (
    <div
      className={`px-4 py-5 sm:px-6 mx-auto space-y-5 w-full ${
        wide ? "max-w-[1680px]" : "max-w-[960px]"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to={backTo} className="text-sm text-brand hover:underline">
            ← 题库首页
          </Link>
          <h1 className="text-xl font-semibold text-text mt-1">{title}</h1>
        </div>
      </div>

      {step != null ? (
        <ol className="flex flex-wrap justify-center gap-2">
          {INGEST_STEPS.map((s) => (
            <li
              key={s.id}
              className={`rounded-full px-3 py-1 text-xs border ${
                s.id === step
                  ? "border-brand bg-brand/10 text-brand"
                  : s.id < step
                    ? "border-border text-text"
                    : "border-border text-text-muted"
              }`}
            >
              {s.id}. {s.label}
            </li>
          ))}
        </ol>
      ) : null}

      {children}
    </div>
  );
}
