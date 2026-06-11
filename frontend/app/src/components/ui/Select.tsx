import { type SelectHTMLAttributes, forwardRef } from "react";
import { cn } from "../../lib/utils";

const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm",
      "focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";

export { Select };
