import { useState } from "react";
import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import type { ToolTraceItem } from "../../api/types";

type Props = {
  items: ToolTraceItem[];
  live?: boolean;
};

const PREVIEW_CHARS = 72;
const AUTO_COLLAPSE_CHARS = 96;

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

function previewLine(text: string): string {
  const one = text.replace(/\s+/g, " ").trim();
  if (one.length <= PREVIEW_CHARS) return one;
  return one.slice(0, PREVIEW_CHARS) + "…";
}

function ToolTraceRow({
  item,
  pending,
  defaultExpanded,
}: {
  item: ToolTraceItem;
  pending: boolean;
  defaultExpanded: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const argsText = formatArgs(item.arguments);
  const output = item.output ?? "";
  const hasOutput = output !== "";
  const canCollapse = hasOutput && !pending && output.length > AUTO_COLLAPSE_CHARS;

  return (
    <div
      className={
        "rounded-lg border text-xs overflow-hidden " +
        (item.ok === false
          ? "border-error/30 bg-error-bg/40"
          : pending
            ? "border-brand/30 bg-brand-light/25"
            : "border-border bg-surface-muted/50")
      }
    >
      <button
        type="button"
        disabled={!canCollapse}
        onClick={() => canCollapse && setExpanded((v) => !v)}
        className={
          "w-full flex items-start gap-2 px-3 py-2 text-left " +
          (canCollapse ? "cursor-pointer hover:bg-white/50" : "cursor-default")
        }
      >
        {canCollapse ? (
          expanded ? (
            <ChevronDown size={14} className="shrink-0 mt-0.5 text-text-muted" />
          ) : (
            <ChevronRight size={14} className="shrink-0 mt-0.5 text-text-muted" />
          )
        ) : (
          <Wrench size={14} className="shrink-0 mt-0.5 text-text-muted" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-text">{item.tool}</span>
            {argsText ? (
              <span className="text-text-muted truncate max-w-[280px]">({argsText})</span>
            ) : null}
            {pending ? (
              <span className="text-brand animate-pulse">执行中…</span>
            ) : item.ok === false ? (
              <span className="text-error">失败</span>
            ) : (
              <span className="text-success">完成</span>
            )}
            {canCollapse && !expanded ? (
              <span className="text-text-muted">· {output.length} 字</span>
            ) : null}
          </div>
          {hasOutput && (!canCollapse || expanded) ? (
            <p className="mt-1.5 text-text leading-relaxed whitespace-pre-wrap break-words">{output}</p>
          ) : null}
          {canCollapse && !expanded ? (
            <p className="mt-1 text-text-muted leading-relaxed truncate">{previewLine(output)}</p>
          ) : null}
        </div>
      </button>
    </div>
  );
}

export function ToolTracePanel({ items, live = false }: Props) {
  if (!items.length) return null;

  return (
    <div className="mb-3 space-y-1.5">
      {items.map((item, i) => {
        const pending = live && item.output === undefined;
        const outputLen = (item.output ?? "").length;
        const defaultExpanded = pending || outputLen <= AUTO_COLLAPSE_CHARS;
        return (
          <ToolTraceRow
            key={`${item.tool}-${i}`}
            item={item}
            pending={pending}
            defaultExpanded={defaultExpanded}
          />
        );
      })}
    </div>
  );
}
