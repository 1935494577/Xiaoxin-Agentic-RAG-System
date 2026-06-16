import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Props = {
  title: string;
  description?: string;
  children?: ReactNode;
  className?: string;
};

export function PageHeader({ title, description, children, className }: Props) {
  return (
    <header className={cn("admin-page-header mb-6", className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-2xl">
          <h2 className="text-xl font-semibold tracking-tight text-text">{title}</h2>
          {description ? (
            <p className="mt-1.5 text-pretty text-sm leading-relaxed text-text-muted">
              {description}
            </p>
          ) : null}
        </div>
        {children ? <div className="flex shrink-0 items-center gap-2">{children}</div> : null}
      </div>
    </header>
  );
}
