import { cn } from "@/lib/utils";
import {
  ASSISTANT_MODE_OPTIONS,
  type AssistantMode,
} from "@/lib/assistantMode";

type Props = {
  value: AssistantMode;
  onChange: (mode: AssistantMode) => void;
  disabled?: boolean;
  className?: string;
};

export function AssistantModeSwitcher({ value, onChange, disabled, className }: Props) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border border-border bg-white p-0.5",
        disabled && "opacity-60 pointer-events-none",
        className
      )}
      role="radiogroup"
      aria-label="助手模式"
    >
      {ASSISTANT_MODE_OPTIONS.map((opt) => {
        const active = value === opt.id;
        return (
          <button
            key={opt.id}
            type="button"
            role="radio"
            aria-checked={active}
            title={opt.description}
            disabled={disabled}
            onClick={() => onChange(opt.id)}
            className={cn(
              "rounded-full px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer",
              active
                ? "bg-brand text-white shadow-sm"
                : "text-text-muted hover:text-text hover:bg-surface-muted"
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
