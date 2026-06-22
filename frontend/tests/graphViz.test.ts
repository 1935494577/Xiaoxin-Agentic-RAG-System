import { describe, expect, it } from "vitest";
import {
  getGraphFocusSet,
  inferOrgLevel,
  isGraphEdgeFocused,
  parseGraphVizFromText,
} from "../src/lib/graphViz";
import type { GraphViz } from "../src/api/types";

describe("inferOrgLevel", () => {
  it("classifies C-suite and department heads", () => {
    expect(inferOrgLevel("CEO")).toBe("executive");
    expect(inferOrgLevel("CTO")).toBe("executive");
    expect(inferOrgLevel("前端负责人")).toBe("director");
    expect(inferOrgLevel("产品总监")).toBe("director");
    expect(inferOrgLevel("HR经理")).toBe("manager");
    expect(inferOrgLevel("测试主管")).toBe("manager");
    expect(inferOrgLevel("高级后端工程师")).toBe("senior");
    expect(inferOrgLevel("算法工程师")).toBe("staff");
  });
});

const graph: GraphViz = {
  center_id: "a",
  nodes: [
    { id: "a", label: "A" },
    { id: "b", label: "B" },
    { id: "c", label: "C" },
  ],
  edges: [
    { from: "a", to: "b", from_label: "A", to_label: "B", label: "汇报" },
    { from: "b", to: "c", from_label: "B", to_label: "C", label: "汇报" },
  ],
};

describe("getGraphFocusSet", () => {
  it("returns null when nothing is selected", () => {
    expect(getGraphFocusSet(graph, null)).toBeNull();
  });

  it("includes selected node and direct neighbors", () => {
    expect(getGraphFocusSet(graph, "b")).toEqual(new Set(["b", "a", "c"]));
  });
});

describe("isGraphEdgeFocused", () => {
  it("treats all edges as focused when nothing is selected", () => {
    expect(isGraphEdgeFocused(graph.edges[0], null)).toBe(true);
  });

  it("only keeps edges incident to the selected node", () => {
    expect(isGraphEdgeFocused(graph.edges[0], "b")).toBe(true);
    expect(isGraphEdgeFocused(graph.edges[1], "b")).toBe(true);
    expect(isGraphEdgeFocused(graph.edges[1], "a")).toBe(false);
  });
});

describe("parseGraphVizFromText", () => {
  it("parses embedded graph JSON from tool output", () => {
    const payload = {
      center_id: "a",
      nodes: [{ id: "a", label: "张三" }],
      edges: [],
    };
    const text = `已生成关系图数据：\n__GRAPH_VIZ_JSON__\n${JSON.stringify(payload)}\n__END_GRAPH_VIZ__`;
    const parsed = parseGraphVizFromText(text);
    expect(parsed?.nodes[0].label).toBe("张三");
  });
});
