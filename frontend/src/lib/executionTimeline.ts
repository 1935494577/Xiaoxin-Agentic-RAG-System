import type { ChatMessage, ExecutionSummary, StreamEvent, ToolTraceItem } from "../api/types";

export type { ExecutionSummary };

export type ExecutionStepKind = "status" | "tool";

export type ExecutionStep = {
  id: string;
  kind: ExecutionStepKind;
  label: string;
  detail?: string;
  pending?: boolean;
  ok?: boolean;
  tool?: string;
  output?: string;
  arguments?: Record<string, unknown>;
  phase?: string;
};

const PHASE_LABELS: Record<string, string> = {
  routing: "路由决策",
  query_understanding: "理解问题",
  retrieving: "检索知识库",
  retrieval_routing: "检索模式",
  generating: "生成回答",
};

let stepCounter = 0;

function nextStepId(prefix: string): string {
  stepCounter += 1;
  return `${prefix}-${stepCounter}`;
}

export function resetExecutionStepIds(): void {
  stepCounter = 0;
}

export function labelForStatusPhase(phase: string): string {
  return PHASE_LABELS[phase] ?? phase;
}

function completePendingStatusSteps(steps: ExecutionStep[]): ExecutionStep[] {
  return steps.map((s) =>
    s.kind === "status" && s.pending ? { ...s, pending: false } : s
  );
}

function upsertStatusStep(steps: ExecutionStep[], evt: Extract<StreamEvent, { type: "status" }>): ExecutionStep[] {
  const completed = completePendingStatusSteps(steps);
  const label = labelForStatusPhase(evt.phase);
  const detailParts: string[] = [];
  if (evt.rag_architecture) detailParts.push(`架构 ${evt.rag_architecture}`);
  if (evt.answer_mode) detailParts.push(evt.answer_mode === "kb" ? "知识库" : "通用");
  if (evt.assistant_mode) detailParts.push(`模式 ${evt.assistant_mode}`);

  return [
    ...completed,
    {
      id: nextStepId("status"),
      kind: "status",
      label,
      phase: evt.phase,
      detail: detailParts.length ? detailParts.join(" · ") : undefined,
      pending: true,
    },
  ];
}

function upsertToolStep(
  steps: ExecutionStep[],
  evt: Extract<StreamEvent, { type: "tool_call" | "tool_result" }>
): ExecutionStep[] {
  if (evt.type === "tool_call") {
    return [
      ...steps,
      {
        id: nextStepId("tool"),
        kind: "tool",
        label: evt.tool,
        tool: evt.tool,
        arguments: evt.arguments,
        pending: true,
      },
    ];
  }

  const next = [...steps];
  for (let i = next.length - 1; i >= 0; i -= 1) {
    const step = next[i];
    if (step.kind === "tool" && step.tool === evt.tool && step.pending) {
      next[i] = {
        ...step,
        output: evt.output,
        ok: evt.ok,
        pending: false,
      };
      return next;
    }
  }

  return [
    ...next,
    {
      id: nextStepId("tool"),
      kind: "tool",
      label: evt.tool,
      tool: evt.tool,
      output: evt.output,
      ok: evt.ok,
      pending: false,
    },
  ];
}

export function applyExecutionStreamEvent(steps: ExecutionStep[], evt: StreamEvent): ExecutionStep[] {
  if (evt.type === "status") {
    return upsertStatusStep(steps, evt);
  }
  if (evt.type === "tool_call" || evt.type === "tool_result") {
    return upsertToolStep(steps, evt);
  }
  if (evt.type === "done") {
    return completePendingStatusSteps(steps);
  }
  return steps;
}

export function buildExecutionSummary(
  steps: ExecutionStep[],
  extras?: {
    answer_mode?: string;
    rag_architecture?: string;
    assistant_mode?: string;
  }
): ExecutionSummary {
  const tools_used = steps
    .filter((s) => s.kind === "tool" && s.tool)
    .map((s) => s.tool as string);
  return {
    steps: steps.length,
    tools_used: [...new Set(tools_used)],
    answer_mode: extras?.answer_mode,
    rag_architecture: extras?.rag_architecture,
    assistant_mode: extras?.assistant_mode,
  };
}

export function stepsFromToolTrace(items: ToolTraceItem[]): ExecutionStep[] {
  return items.map((item, index) => ({
    id: `tool-hist-${index}`,
    kind: "tool" as const,
    label: item.tool,
    tool: item.tool,
    arguments: item.arguments,
    output: item.output,
    ok: item.ok,
    pending: item.output === undefined,
  }));
}

export function stepsFromMessageMeta(meta?: ChatMessage["meta"]): ExecutionStep[] {
  if (!meta) return [];
  const toolSteps = stepsFromToolTrace(meta.tool_trace ?? []);
  if (toolSteps.length) return toolSteps;
  const summary = meta.execution_summary;
  if (summary && summary.steps > 0) {
    return [
      {
        id: "summary-only",
        kind: "status",
        label: `已完成 ${summary.steps} 步`,
        detail: [
          summary.rag_architecture ? `架构 ${summary.rag_architecture}` : "",
          summary.answer_mode ? (summary.answer_mode === "kb" ? "知识库" : "通用") : "",
        ]
          .filter(Boolean)
          .join(" · "),
        pending: false,
      },
    ];
  }
  return [];
}

export function finalizeExecutionSteps(steps: ExecutionStep[]): ExecutionStep[] {
  return steps.map((s) => (s.pending ? { ...s, pending: false } : s));
}
