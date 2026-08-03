import type { LucideIcon } from "lucide-react";
import { cn } from "../../lib/utils";

type Props = {
  label: string;
  value: string;
  variant?: "default" | "success" | "warning";
  icon?: LucideIcon;
};

const variants = {
  default: "bg-surface border-border",
  success: "bg-success-bg border-success/20",
  warning: "bg-warning-bg border-warning/20",
};

const valueVariants = {
  default: "text-brand",
  success: "text-success",
  warning: "text-warning",
};

export function MetricCard({ label, value, variant = "default", icon: Icon }: Props) {
  return (
    <div className={cn("rounded-xl border p-4 shadow-card", variants[variant])}>
      <p className="mb-1 flex items-center gap-1.5 text-sm text-text-muted">
        {Icon ? <Icon className="h-4 w-4 shrink-0" aria-hidden /> : null}
        {label}
      </p>
      <p className={cn("text-2xl font-bold", valueVariants[variant])}>{value}</p>
    </div>
  );
}
