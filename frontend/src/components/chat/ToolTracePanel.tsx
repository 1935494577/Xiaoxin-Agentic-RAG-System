import type { ToolTraceItem } from "../../api/types";

type Props = {
  items: ToolTraceItem[];
  live?: boolean;
};

function formatArgs(args?: Record<string, unknown>): string {
  if (!args || !Object.keys(args).length) return "";
  try {
    return Object.entries(args)
      .map(([k, v]) => `${k}=${String(v)}`)
      .join(", ");
  } catch {
    return "";
  }
}

export function ToolTracePanel({ items, live = false }: Props) {
  if (!items.length) return null;

  return (
    <div className="mb-3 space-y-2">
      {items.map((item, i) => {
        const argsText = formatArgs(item.arguments);
        const pending = live && item.output === undefined;
        return (
          <div
            key={`${item.tool}-${i}`}
            className={
              "rounded-lg border text-xs px-3 py-2 " +
              (item.ok === false
                ? "border-error/30 bg-error-bg/50 text-error"
                : pending
                  ? "border-brand/30 bg-brand-light/30 text-text"
                  : "border-border bg-surface-muted/60 text-text-muted")
            }
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-text">🔧 {item.tool}</span>
              {argsText ? <span className="text-text-muted">({argsText})</span> : null}
              {pending ? (
                <span className="text-brand animate-pulse">执行中…</span>
              ) : item.ok === false ? (
                <span>失败</span>
              ) : (
                <span className="text-success">完成</span>
              )}
            </div>
            {item.output !== undefined && item.output !== "" ? (
              <p className="mt-1.5 text-text leading-relaxed whitespace-pre-wrap break-words">
                {item.output}
              </p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
