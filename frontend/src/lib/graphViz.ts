import type { GraphViz } from "../api/types";

const START = "__GRAPH_VIZ_JSON__";
const END = "__END_GRAPH_VIZ__";

/** 从工具输出或 SSE 文本中解析关系图数据。 */
export function parseGraphVizFromText(text: string): GraphViz | null {
  if (!text.includes(START)) return null;
  try {
    const start = text.indexOf(START) + START.length;
    const end = text.indexOf(END, start);
    if (end < 0) return null;
    const raw = text.slice(start, end).trim();
    const data = JSON.parse(raw) as GraphViz;
    if (data && Array.isArray(data.nodes)) return data;
  } catch {
    return null;
  }
  return null;
}

/** 从消息 meta 或 tool_trace 中提取关系图。 */
export function graphVizFromMessageMeta(meta?: {
  graph_viz?: GraphViz;
  tool_trace?: Array<{ tool?: string; output?: string }>;
}): GraphViz | null {
  if (meta?.graph_viz?.nodes?.length) return meta.graph_viz;
  const trace = meta?.tool_trace;
  if (!trace?.length) return null;
  for (let i = trace.length - 1; i >= 0; i -= 1) {
    const row = trace[i];
    if (row.tool === "show_relationship_graph" && row.output) {
      const parsed = parseGraphVizFromText(row.output);
      if (parsed) return parsed;
    }
  }
  return null;
}
