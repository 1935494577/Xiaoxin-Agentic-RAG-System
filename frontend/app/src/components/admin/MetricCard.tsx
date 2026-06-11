import { cn } from "../../lib/utils";

type Props = {
  label: string;
  value: string;
  variant?: "default" | "success" | "warning";
};

const variants = {
  default: "bg-white border-border",
  success: "bg-success-bg border-success/20",
  warning: "bg-warning-bg border-warning/20",
};

const valueVariants = {
  default: "text-brand",
  success: "text-success",
  warning: "text-warning",
};

export function MetricCard({ label, value, variant = "default" }: Props) {
  return (
    <div className={cn("rounded-xl border p-4", variants[variant])}>
      <p className="text-sm text-text-muted mb-1">{label}</p>
      <p className={cn("text-2xl font-bold", valueVariants[variant])}>{value}</p>
    </div>
  );
}
