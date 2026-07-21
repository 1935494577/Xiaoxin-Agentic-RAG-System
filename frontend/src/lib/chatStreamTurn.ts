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
    return {
      ...acc,
      toolTrace: applyToolStreamEvent(acc.toolTrace, evt),
      executionSteps: applyExecutionStreamEvent(acc.executionSteps, evt),
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
      },
    };
  }
  return acc;
}
