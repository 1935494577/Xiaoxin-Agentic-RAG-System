import { describe, expect, it } from "vitest";
import { getNodeRelations } from "../src/lib/graphViz";
import type { GraphViz } from "../src/api/types";

const graph: GraphViz = {
  center_id: "zhu",
  nodes: [
    { id: "zhu", label: "朱琳", title: "算法工程师" },
    { id: "wu", label: "吴迪", title: "AI实验室负责人" },
    { id: "lin", label: "林雪", title: "CTO" },
  ],
  edges: [
    { from: "zhu", to: "wu", from_label: "朱琳", to_label: "吴迪", label: "汇报" },
    { from: "wu", to: "lin", from_label: "吴迪", to_label: "林雪", label: "汇报" },
    { from: "wu", to: "zhu", from_label: "吴迪", to_label: "朱琳", label: "虚线管辖" },
  ],
};

describe("getNodeRelations", () => {
  it("maps reporting edges by direction for the selected node", () => {
    const rel = getNodeRelations(graph, "zhu");
    expect(rel.reportsTo).toEqual(["吴迪"]);
    expect(rel.directReports).toEqual([]);
    expect(rel.managedBy).toEqual([]);
    expect(rel.dottedManages).toEqual([]);
    expect(rel.dottedManagedBy).toEqual(["吴迪"]);
  });

  it("does not treat incoming dotted edges as reports-to", () => {
    const rel = getNodeRelations(graph, "wu");
    expect(rel.reportsTo).toEqual(["林雪"]);
    expect(rel.directReports).toEqual(["朱琳"]);
    expect(rel.dottedManages).toEqual(["朱琳"]);
    expect(rel.reportsTo).not.toContain("朱琳");
  });
});
