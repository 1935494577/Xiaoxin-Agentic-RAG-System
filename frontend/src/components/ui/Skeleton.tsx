import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-md bg-border/70", className)}
      {...props}
    />
  );
}

/** 页面/卡片加载占位：标题条 + N 行内容条 */
export function SkeletonCard({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface px-5 py-4 shadow-card",
        className
      )}
      role="status"
      aria-label="加载中"
    >
      <Skeleton className="h-4 w-40" />
      <div className="mt-4 space-y-3">
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} className={cn("h-3.5", i % 3 === 2 ? "w-2/3" : "w-full")} />
        ))}
      </div>
    </div>
  );
}
