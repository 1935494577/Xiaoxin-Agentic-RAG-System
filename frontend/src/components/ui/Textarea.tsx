import { type TextareaHTMLAttributes, forwardRef } from "react";
import { cn } from "../../lib/utils";

const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[80px] w-full rounded-lg border border-border bg-white px-3 py-2 text-sm",
        "placeholder:text-text-muted",
        "focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";

export { Textarea };
