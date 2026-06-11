import { type ReactNode, useEffect, useRef } from "react";
import { Button } from "./Button";

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  onConfirm?: () => void;
  variant?: "default" | "destructive";
  loading?: boolean;
};

export function Dialog({
  open,
  onClose,
  title,
  children,
  confirmLabel,
  onConfirm,
  variant = "default",
  loading,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      const handler = (e: KeyboardEvent) => {
        if (e.key === "Escape") onClose();
      };
      document.addEventListener("keydown", handler);
      return () => document.removeEventListener("keydown", handler);
    }
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/40" onClick={onClose} />
      <div
        ref={ref}
        className="relative bg-white rounded-xl shadow-lg max-w-md w-full mx-4 p-6 z-10"
      >
        <h3 className="text-lg font-semibold text-text mb-3">{title}</h3>
        <div className="text-sm text-text-muted mb-6">{children}</div>
        <div className="flex justify-end gap-2">
          <Button variant="default" size="sm" onClick={onClose} disabled={loading}>
            取消
          </Button>
          {confirmLabel && onConfirm && (
            <Button
              variant={variant === "destructive" ? "destructive" : "primary"}
              size="sm"
              onClick={onConfirm}
              disabled={loading}
            >
              {loading ? "处理中..." : confirmLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
