import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, Circle, Loader2, Wrench } from "lucide-react";
import type { ExecutionStep } from "@/lib/executionTimeline";

type Props = {
  steps: ExecutionStep[];
  live?: boolean;
  className?: string;
};

function StepIcon({ step }: { step: ExecutionStep }) {
  if (step.pending) {
    return <Loader2 size={14} className="shrink-0 text-brand animate-spin" aria-hidden />;
  }
  if (step.kind === "tool") {
    return <Wrench size={14} className="shrink-0 text-text-muted" aria-hidden />;
  }
  return (
    <Circle
      size={10}
      className={"shrink-0 " + (step.ok === false ? "text-error fill-error" : "text-success fill-success")}
      aria-hidden
    />
  );
}

function StepRow({ step }: { step: ExecutionStep }) {
  return (
    <li className="flex gap-2 text-xs leading-relaxed">
      <div className="mt-0.5">
        <StepIcon step={step} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span className="font-medium text-text">{step.label}</span>
          {step.pending ? <span className="text-brand">执行中…</span> : null}
          {!step.pending && step.ok === false ? <span className="text-error">失败</span> : null}
          {step.detail ? <span className="text-text-muted">{step.detail}</span> : null}
        </div>
        {step.output ? (
          <p className="mt-1 text-text-muted whitespace-pre-wrap break-words line-clamp-3">{step.output}</p>
        ) : null}
      </div>
    </li>
  );
}

export function ExecutionTimeline({ steps, live = false, className = "" }: Props) {
  const [open, setOpen] = useState(live);

  useEffect(() => {
    if (live) setOpen(true);
  }, [live, steps.length]);

  if (!steps.length) return null;

  const toolCount = steps.filter((s) => s.kind === "tool").length;
  const summary =
    toolCount > 0
      ? `${steps.length} 步 · ${toolCount} 个工具`
      : `${steps.length} 步`;

  return (
    <div className={"rounded-lg border border-border bg-surface-muted/40 " + className}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-text hover:bg-surface/60 rounded-lg cursor-pointer border-none bg-transparent"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        执行步骤
        <span className="font-normal text-text-muted">({summary})</span>
        {live ? <span className="ml-auto text-brand animate-pulse">进行中</span> : null}
      </button>
      {open ? (
        <ol className="px-3 pb-3 pt-0 space-y-2 border-t border-border/60 list-none m-0">
          {steps.map((step) => (
            <StepRow key={step.id} step={step} />
          ))}
        </ol>
      ) : null}
    </div>
  );
}
