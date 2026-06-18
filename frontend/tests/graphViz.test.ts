import { describe, expect, it } from "vitest";
import { parseGraphVizFromText } from "../src/lib/graphViz";

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
