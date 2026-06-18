import type { GraphViz, GraphVizEdge } from "../api/types";

const START = "__GRAPH_VIZ_JSON__";
const END = "__END_GRAPH_VIZ__";

export type NodeRelationGroup = {
  reportsTo: string[];
  directReports: string[];
  manages: string[];
  managedBy: string[];
  dottedReports: string[];
  dottedManages: string[];
  dottedManagedBy: string[];
  dottedDirectReports: string[];
  dottedGuides: string[];
  collaborations: string[];
};

/** 组织岗位层级（用于关系图配色）。 */
export type OrgLevel = "executive" | "director" | "manager" | "senior" | "staff" | "unknown";

export type OrgLevelStyle = {
  label: string;
  color: string;
  border: string;
  symbolSize: number;
};

/** 层级顺序：与 ECharts categories 下标一致。 */
export const ORG_LEVEL_ORDER: OrgLevel[] = [
  "executive",
  "director",
  "manager",
  "senior",
  "staff",
  "unknown",
];

export const ORG_LEVEL_STYLES: Record<OrgLevel, OrgLevelStyle> = {
  executive: { label: "高管层", color: "#7c3aed", border: "#6d28d9", symbolSize: 54 },
  director: { label: "负责人/总监", color: "#2563eb", border: "#1d4ed8", symbolSize: 48 },
  manager: { label: "经理/主管", color: "#0891b2", border: "#0e7490", symbolSize: 44 },
  senior: { label: "高级/专家", color: "#059669", border: "#047857", symbolSize: 40 },
  staff: { label: "专员/工程师", color: "#64748b", border: "#475569", symbolSize: 36 },
  unknown: { label: "其他", color: "#94a3b8", border: "#64748b", symbolSize: 38 },
};

/** 根据职务 title 推断岗位层级。 */
export function inferOrgLevel(title?: string | null): OrgLevel {
  const t = (title || "").trim();
  if (!t) return "unknown";
  if (/CEO|CTO|CFO|COO|首席|总裁|总经理/i.test(t)) return "executive";
  if (/总监|负责人|顾问|Director|Head/i.test(t)) return "director";
  if (/经理|主管|组长|Manager/i.test(t)) return "manager";
  if (/高级|专家|Senior|Principal/i.test(t)) return "senior";
  if (/工程师|专员|会计|出纳|标注|设计|分析|助理|员/i.test(t)) return "staff";
  return "unknown";
}

export function orgLevelCategoryIndex(level: OrgLevel): number {
  return ORG_LEVEL_ORDER.indexOf(level);
}

export function nodeSymbolSize(level: OrgLevel, opts?: { isCenter?: boolean; isSelected?: boolean }): number {
  const base = ORG_LEVEL_STYLES[level].symbolSize;
  if (opts?.isSelected) return base + 8;
  if (opts?.isCenter) return base + 6;
  return base;
}

/** 选中节点时，返回该节点及其一度邻居 id 集合；未选中时返回 null。 */
export function getGraphFocusSet(graph: GraphViz, selectedNodeId: string | null): Set<string> | null {
  if (!selectedNodeId) return null;
  const focus = new Set<string>([selectedNodeId]);
  for (const e of graph.edges) {
    if (e.from === selectedNodeId) focus.add(e.to);
    if (e.to === selectedNodeId) focus.add(e.from);
  }
  return focus;
}

/** 选中状态下，边是否与选中节点直接相连。 */
export function isGraphEdgeFocused(edge: GraphVizEdge, selectedNodeId: string | null): boolean {
  if (!selectedNodeId) return true;
  return edge.from === selectedNodeId || edge.to === selectedNodeId;
}

/** 汇总某节点在图中的汇报/管辖/协作关系（用于详情面板）。 */
export function getNodeRelations(graph: GraphViz, nodeId: string): NodeRelationGroup {
  const reportsTo: string[] = [];
  const directReports: string[] = [];
  const manages: string[] = [];
  const managedBy: string[] = [];
  const dottedReports: string[] = [];
  const dottedManages: string[] = [];
  const dottedManagedBy: string[] = [];
  const dottedDirectReports: string[] = [];
  const dottedGuides: string[] = [];
  const collaborations: string[] = [];

  for (const e of graph.edges) {
    if (e.from === nodeId) {
      if (e.label === "汇报") reportsTo.push(e.to_label);
      else if (e.label === "虚线汇报") dottedReports.push(e.to_label);
      else if (e.label === "管辖") manages.push(e.to_label);
      else if (e.label === "虚线管辖") dottedManages.push(e.to_label);
      else if (e.label === "虚线指导") dottedGuides.push(e.to_label);
      else if (e.label === "协作") collaborations.push(e.to_label);
    }
    if (e.to === nodeId) {
      if (e.label === "汇报") directReports.push(e.from_label);
      else if (e.label === "虚线汇报") dottedDirectReports.push(e.from_label);
      else if (e.label === "管辖") managedBy.push(e.from_label);
      else if (e.label === "虚线管辖") dottedManagedBy.push(e.from_label);
      else if (e.label === "虚线指导") dottedGuides.push(e.from_label);
      else if (e.label === "协作") collaborations.push(e.from_label);
    }
  }

  const uniq = (xs: string[]) => [...new Set(xs)];

  return {
    reportsTo: uniq(reportsTo),
    directReports: uniq(directReports),
    manages: uniq(manages),
    managedBy: uniq(managedBy),
    dottedReports: uniq(dottedReports),
    dottedManages: uniq(dottedManages),
    dottedManagedBy: uniq(dottedManagedBy),
    dottedDirectReports: uniq(dottedDirectReports),
    dottedGuides: uniq(dottedGuides),
    collaborations: uniq(collaborations),
  };
}

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
