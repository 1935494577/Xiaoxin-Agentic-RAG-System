import { type ReactNode } from "react";
import { cn } from "../../lib/utils";

type Variant = "default" | "success" | "warning" | "error" | "info";

const variantClasses: Record<Variant, string> = {
  default: "bg-surface-muted text-text-muted",
  success: "bg-success-bg text-success",
  warning: "bg-warning-bg text-warning",
  error: "bg-error-bg text-error",
  info: "bg-brand-light text-brand",
};

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold",
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
