import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "../../lib/utils";

type Variant = "default" | "primary" | "destructive" | "ghost";
type Size = "sm" | "md" | "icon";

const variantClasses: Record<Variant, string> = {
  default: "bg-white border border-border text-text hover:bg-surface-muted",
  primary: "bg-brand text-white hover:bg-brand-dark",
  destructive: "bg-error text-white hover:opacity-90",
  ghost: "bg-transparent text-text-muted hover:bg-surface-muted hover:text-text",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs rounded-md",
  md: "px-4 py-2 text-sm rounded-lg",
  icon: "p-2 rounded-lg",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

const Button = forwardRef<HTMLButtonElement, Props>(
  ({ className, variant = "default", size = "md", disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 font-medium transition-colors",
        "disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      disabled={disabled}
      {...props}
    />
  )
);
Button.displayName = "Button";

export { Button };
export type { Props as ButtonProps };
