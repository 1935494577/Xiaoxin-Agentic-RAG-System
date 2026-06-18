import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { GraphViz, GraphVizEdge, GraphVizNode } from "../../api/types";

type Props = {
  graph: GraphViz;
  height: number;
  chartKey: string;
  scaleMax?: number;
};

function nodeTooltip(node: GraphVizNode): string {
  const lines = [node.label];
  if (node.title) lines.push(node.title);
  if (node.department) lines.push(node.department);
  if (node.bio) lines.push(node.bio);
  return lines.join("<br/>");
}

function buildOption(graph: GraphViz, height: number, scaleMax = 2.5): EChartsOption {
  const centerId = graph.center_id;
  const nodeMap = new Map(graph.nodes.map((n) => [n.id, n]));

  const data = graph.nodes.map((n) => {
    const isCenter = n.id === centerId;
    return {
      id: n.id,
      name: n.label,
      symbolSize: isCenter ? 58 : 44,
      category: isCenter ? 0 : 1,
      value: n.title || n.department || "",
      draggable: true,
      label: {
        show: true,
        formatter: () => {
          const title = n.title ? `\n${n.title}` : "";
          return `${n.label}${title}`;
        },
        fontSize: isCenter ? 13 : 12,
        lineHeight: 16,
      },
      itemStyle: {
        color: isCenter ? "#2563eb" : "#64748b",
        borderColor: isCenter ? "#1d4ed8" : "#475569",
        borderWidth: isCenter ? 2 : 1,
        shadowBlur: isCenter ? 12 : 4,
        shadowColor: "rgba(37, 99, 235, 0.25)",
      },
    };
  });

  const links = graph.edges.map((e: GraphVizEdge) => ({
    source: e.from,
    target: e.to,
    label: {
      show: true,
      formatter: e.label,
      fontSize: 10,
      color: "#64748b",
    },
    lineStyle: {
      color: e.label === "汇报" ? "#94a3b8" : "#cbd5e1",
      width: e.label === "汇报" ? 2 : 1.5,
      curveness: 0.15,
    },
    symbol: ["none", "arrow"],
    symbolSize: 8,
  }));

  return {
    animationDuration: 600,
    animationEasingUpdate: "quinticInOut",
    tooltip: {
      trigger: "item",
      formatter: (params: unknown) => {
        const p = params as { dataType?: string; data?: { id?: string; name?: string } };
        if (p.dataType === "edge") return "";
        const id = p.data?.id;
        const node = id ? nodeMap.get(id) : graph.nodes.find((n) => n.label === p.data?.name);
        return node ? nodeTooltip(node) : String(p.data?.name || "");
      },
    },
    legend: {
      data: ["中心人物", "关联人物"],
      bottom: 0,
      textStyle: { color: "#64748b", fontSize: 11 },
    },
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        scaleLimit: { min: 0.25, max: scaleMax },
        categories: [{ name: "中心人物" }, { name: "关联人物" }],
        data,
        links,
        force: {
          repulsion: Math.max(280, graph.nodes.length * 28),
          gravity: 0.08,
          edgeLength: [80, 160],
          friction: 0.35,
          layoutAnimation: true,
        },
        emphasis: {
          focus: "adjacency",
          lineStyle: { width: 3 },
          itemStyle: { shadowBlur: 16 },
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
}: Props) {
  const option = useMemo(() => buildOption(graph, height, scaleMax), [graph, height, scaleMax]);

  return (
    <ReactECharts
      key={chartKey}
      option={option}
      style={{ height, width: "100%" }}
      opts={{ renderer: "canvas" }}
      notMerge
      lazyUpdate
    />
  );
}
