import type { StreamEvent, ToolTraceItem } from "../api/types";

/** 合并 SSE 工具事件到 trace 列表（流式展示用）。 */
export function applyToolStreamEvent(items: ToolTraceItem[], evt: StreamEvent): ToolTraceItem[] {
  if (evt.type === "tool_call") {
    return [...items, { tool: evt.tool, arguments: evt.arguments }];
  }
  if (evt.type === "tool_result") {
    const next = [...items];
    for (let i = next.length - 1; i >= 0; i -= 1) {
      if (next[i].tool === evt.tool && next[i].output === undefined) {
        next[i] = {
          ...next[i],
          output: evt.output,
          ok: evt.ok,
        };
        return next;
      }
    }
    return [...next, { tool: evt.tool, output: evt.output, ok: evt.ok }];
  }
  return items;
}
