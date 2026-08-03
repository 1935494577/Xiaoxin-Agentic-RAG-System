import type { LucideIcon } from "lucide-react";
import { Button } from "./Button";

type Props = {
  icon: LucideIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
};

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: Props) {
  return (
    <div
      className={
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-surface-muted/40 px-6 py-12 text-center " +
        (className ?? "")
      }
    >
      <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-light text-brand">
        <Icon className="h-5 w-5" aria-hidden />
      </div>
      <p className="text-sm font-semibold text-text">{title}</p>
      {description ? (
        <p className="mt-1.5 max-w-md text-pretty text-xs leading-relaxed text-text-muted">
          {description}
        </p>
      ) : null}
      {actionLabel && onAction ? (
        <Button variant="primary" size="sm" className="mt-4" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
