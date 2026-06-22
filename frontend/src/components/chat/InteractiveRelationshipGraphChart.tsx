import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { GraphViz, GraphVizEdge, GraphVizNode } from "../../api/types";
import { getGraphFocusSet, inferOrgLevel, isGraphEdgeFocused, nodeSymbolSize, ORG_LEVEL_ORDER, ORG_LEVEL_STYLES } from "../../lib/graphViz";

type Props = {
  graph: GraphViz;
  height: number;
  chartKey: string;
  scaleMax?: number;
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
};

function nodeTooltip(node: GraphVizNode): string {
  const lines = [node.label];
  if (node.title) lines.push(node.title);
  if (node.department) lines.push(node.department);
  if (node.bio) {
    const preview = node.bio.length > 80 ? `${node.bio.slice(0, 80)}…` : node.bio;
    lines.push(preview);
  }
  lines.push('<span style="color:#94a3b8;font-size:11px">点击查看详情</span>');
  return lines.join("<br/>");
}

function edgeLineStyle(label: string) {
  if (label === "汇报") {
    return { color: "#94a3b8", width: 2, type: "solid" as const, curveness: 0.15 };
  }
  if (label.startsWith("虚线")) {
    return { color: "#a78bfa", width: 1.5, type: "dashed" as const, curveness: 0.2 };
  }
  if (label === "协作") {
    return { color: "#34d399", width: 1.5, type: "dotted" as const, curveness: 0.25 };
  }
  return { color: "#cbd5e1", width: 1.5, type: "solid" as const, curveness: 0.15 };
}

function edgeTouchesNode(edge: GraphVizEdge, nodeId: string | null | undefined): boolean {
  if (!nodeId) return false;
  return edge.from === nodeId || edge.to === nodeId;
}

function buildOption(
  graph: GraphViz,
  height: number,
  scaleMax = 2.5,
  selectedNodeId?: string | null
): EChartsOption {
  const centerId = graph.center_id;
  const nodeMap = new Map(graph.nodes.map((n) => [n.id, n]));
  const focusSet = getGraphFocusSet(graph, selectedNodeId ?? null);
  const focusActive = focusSet !== null;

  const usedLevels = new Set(graph.nodes.map((n) => inferOrgLevel(n.title)));
  const activeLevels = ORG_LEVEL_ORDER.filter((lv) => usedLevels.has(lv));
  const levelToCategory = new Map(activeLevels.map((lv, i) => [lv, i]));
  const categories = activeLevels.map((lv) => ({
    name: ORG_LEVEL_STYLES[lv].label,
    itemStyle: { color: ORG_LEVEL_STYLES[lv].color },
  }));

  const data = graph.nodes.map((n) => {
    const isCenter = n.id === centerId;
    const isSelected = selectedNodeId === n.id;
    const inFocus = !focusActive || focusSet!.has(n.id);
    const dimmed = focusActive && !inFocus;
    const level = inferOrgLevel(n.title);
    const levelStyle = ORG_LEVEL_STYLES[level];
    const size = dimmed ? 32 : nodeSymbolSize(level, { isCenter, isSelected });
    return {
      id: n.id,
      name: n.label,
      symbolSize: size,
      category: levelToCategory.get(level) ?? 0,
      value: n.title || n.department || "",
      draggable: true,
      label: {
        show: !dimmed,
        formatter: () => {
          const title = n.title ? `\n${n.title}` : "";
          return `${n.label}${title}`;
        },
        fontSize: isCenter || level === "executive" ? 13 : 12,
        lineHeight: 16,
        opacity: dimmed ? 0.15 : 1,
      },
      itemStyle: {
        color: dimmed ? "#e2e8f0" : isSelected ? "#1d4ed8" : levelStyle.color,
        borderColor: dimmed ? "#f1f5f9" : isSelected ? "#1e40af" : levelStyle.border,
        borderWidth: isSelected || isCenter ? 2 : 1,
        opacity: dimmed ? 0.12 : 1,
        shadowBlur: isSelected ? 16 : isCenter ? 12 : dimmed ? 0 : 6,
        shadowColor: isSelected
          ? "rgba(29, 78, 216, 0.35)"
          : `${levelStyle.color}40`,
      },
    };
  });

  const links = graph.edges.map((e: GraphVizEdge) => {
    const style = edgeLineStyle(e.label);
    const edgeFocused = isGraphEdgeFocused(e, selectedNodeId ?? null);
    const dimmed = focusActive && !edgeFocused;
    return {
      source: e.from,
      target: e.to,
      label: {
        show: edgeFocused,
        formatter: e.label,
        fontSize: 10,
        color: dimmed ? "#cbd5e1" : "#64748b",
        opacity: dimmed ? 0.15 : 1,
      },
      lineStyle: {
        ...style,
        opacity: dimmed ? 0.08 : 0.9,
        width: edgeFocused && edgeTouchesNode(e, selectedNodeId) ? style.width + 0.5 : style.width,
      },
      symbol: ["none", "arrow"],
      symbolSize: 8,
    };
  });

  return {
    animationDuration: 600,
    animationEasingUpdate: "quinticInOut",
    tooltip: {
      trigger: "item",
      formatter: (params: unknown) => {
        const p = params as {
          dataType?: string;
          data?: { id?: string; name?: string; source?: string; target?: string };
        };
        if (p.dataType === "edge") {
          const edge = graph.edges.find(
            (e) => e.from === p.data?.source && e.to === p.data?.target
          );
          if (!edge) return "";
          return `${edge.from_label} <b>${edge.label}</b> ${edge.to_label}`;
        }
        const id = p.data?.id;
        const node = id ? nodeMap.get(id) : graph.nodes.find((n) => n.label === p.data?.name);
        return node ? nodeTooltip(node) : String(p.data?.name || "");
      },
    },
    legend: {
      data: categories.map((c) => c.name),
      bottom: 0,
      type: "scroll",
      textStyle: { color: "#64748b", fontSize: 11 },
    },
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        scaleLimit: { min: 0.25, max: scaleMax },
        categories,
        data,
        links,
        force: {
          repulsion: Math.max(280, graph.nodes.length * 28),
          gravity: 0.08,
          edgeLength: [80, 160],
          friction: 0.35,
          layoutAnimation: true,
        },
        emphasis: focusActive
          ? {
              focus: "none",
              scale: false,
              itemStyle: { shadowBlur: 16 },
              lineStyle: { width: 3 },
            }
          : {
              focus: "adjacency",
              lineStyle: { width: 3 },
              itemStyle: { shadowBlur: 16 },
            },
        blur: focusActive
          ? undefined
          : {
              itemStyle: { opacity: 0.15 },
              lineStyle: { opacity: 0.08 },
            },
        lineStyle: { opacity: 0.85 },
        height: height - 40,
      },
    ],
  };
}

export default function InteractiveRelationshipGraphChart({
  graph,
  height,
  chartKey,
  scaleMax = 2.5,
  selectedNodeId = null,
  onNodeSelect,
}: Props) {
  const option = useMemo(
    () => buildOption(graph, height, scaleMax, selectedNodeId),
    [graph, height, scaleMax, selectedNodeId]
  );

  const onEvents = useMemo(
    () => ({
      click: (params: unknown) => {
        if (!onNodeSelect) return;
        const p = params as { dataType?: string; data?: { id?: string } };
        if (p.dataType === "node" && p.data?.id) {
          onNodeSelect(p.data.id);
        }
      },
    }),
    [onNodeSelect]
  );

  return (
    <ReactECharts
      key={chartKey}
      option={option}
      style={{ height, width: "100%" }}
      opts={{ renderer: "canvas" }}
      notMerge
      lazyUpdate
      onEvents={onEvents}
    />
  );
}
