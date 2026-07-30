import type { AssistantMode } from "./assistantMode";
import type { ChatMessage, GraphViz, StreamEvent, ToolTraceItem } from "../api/types";
import {
  applyExecutionStreamEvent,
  buildExecutionSummary,
  finalizeExecutionSteps,
  type ExecutionStep,
} from "./executionTimeline";
import { applyToolStreamEvent } from "./streamTools";

export type StreamTurnAccum = {
  assistant: string;
  streamError: string;
  meta: ChatMessage["meta"];
  toolTrace: ToolTraceItem[];
  executionSteps: ExecutionStep[];
  graphViz?: GraphViz;
  needsClarify: boolean;
  clarifyEvt: Extract<StreamEvent, { type: "clarify" }> | null;
};

function uiBlocksFromToolResult(
  tool: string,
  output: string,
  existing: NonNullable<ChatMessage["meta"]>["ui_blocks"] = [],
): NonNullable<ChatMessage["meta"]>["ui_blocks"] {
  if (!output) return existing || [];
  const prev = existing || [];
  try {
    const j = JSON.parse(output) as {
      ok?: boolean;
      ui_block?: {
        type?: string;
        source_paper_id?: string;
        paper_id?: string;
        title?: string;
        items?: Array<{
          id?: string;
          title?: string;
          source_filename?: string;
          question_count?: number;
        }>;
      };
    };
    if (!j.ok || !j.ui_block) return prev;

    if (tool === "present_exam_paper") {
      const b = j.ui_block;
      const sid = String(b?.source_paper_id || b?.paper_id || "").trim();
      if (!sid) return prev;
      const block = {
        type: "exam_paper",
        source_paper_id: sid,
        paper_id: b?.paper_id,
        title: b?.title,
      };
      if (prev.some((x) => x.source_paper_id === sid || x.paper_id === sid)) return prev;
      return [...prev, block];
    }

    if (tool === "search_exam_papers" && j.ui_block.type === "exam_candidates") {
      const items = j.ui_block.items || [];
      if (!items.length) return prev;
      const without = prev.filter((x) => x.type !== "exam_candidates");
      return [...without, { type: "exam_candidates", items }];
    }
  } catch {
    /* ignore */
  }
  return prev;
}

export function createStreamTurnAccum(): StreamTurnAccum {
  return {
    assistant: "",
    streamError: "",
    meta: {},
    toolTrace: [],
    executionSteps: [],
    needsClarify: false,
    clarifyEvt: null,
  };
}

/** Fold one SSE event into streaming turn state (used by ChatPage). */
export function reduceStreamTurnEvent(
  acc: StreamTurnAccum,
  evt: StreamEvent,
  assistantMode: AssistantMode
): StreamTurnAccum {
  if (evt.type === "token") {
    return { ...acc, assistant: acc.assistant + evt.content };
  }
  if (evt.type === "clarify") {
    return { ...acc, clarifyEvt: evt };
  }
  if (evt.type === "tool_call" || evt.type === "tool_result") {
    const toolTrace = applyToolStreamEvent(acc.toolTrace, evt);
    let ui_blocks = acc.meta?.ui_blocks;
    if (evt.type === "tool_result") {
      ui_blocks = uiBlocksFromToolResult(evt.tool, evt.output, ui_blocks);
    }
    return {
      ...acc,
      toolTrace,
      executionSteps: applyExecutionStreamEvent(acc.executionSteps, evt),
      meta: { ...acc.meta, ui_blocks },
    };
  }
  if (evt.type === "status") {
    return {
      ...acc,
      executionSteps: applyExecutionStreamEvent(acc.executionSteps, evt),
    };
  }
  if (evt.type === "graph_viz") {
    return { ...acc, graphViz: evt.graph };
  }
  if (evt.type === "error") {
    return { ...acc, streamError: evt.message };
  }
  if (evt.type === "done") {
    const executionSteps = applyExecutionStreamEvent(acc.executionSteps, evt);
    const fromDone = evt.ui_blocks?.length ? evt.ui_blocks : undefined;
    return {
      ...acc,
      assistant: evt.answer || acc.assistant,
      needsClarify: Boolean(evt.needs_clarify),
      executionSteps,
      meta: {
        sources: evt.sources,
        source_refs: evt.source_refs,
        answer_mode: evt.answer_mode,
        rag_architecture: evt.rag_architecture,
        verified: evt.verified,
        trace_id: evt.trace_id,
        tool_trace: evt.tool_trace?.length ? evt.tool_trace : acc.toolTrace,
        graph_viz: evt.graph_viz ?? acc.graphViz,
        assistant_mode: evt.assistant_mode ?? assistantMode,
        execution_summary: buildExecutionSummary(finalizeExecutionSteps(executionSteps), {
          answer_mode: evt.answer_mode,
          rag_architecture: evt.rag_architecture,
          assistant_mode: evt.assistant_mode ?? assistantMode,
        }),
        ui_blocks: fromDone || acc.meta?.ui_blocks,
      },
    };
  }
  return acc;
}
