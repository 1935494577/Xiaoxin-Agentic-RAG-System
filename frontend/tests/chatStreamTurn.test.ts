import { describe, expect, it } from "vitest";
import { createStreamTurnAccum, reduceStreamTurnEvent } from "../src/lib/chatStreamTurn";
import type { GraphViz } from "../src/api/types";

const sampleGraph: GraphViz = {
  center_id: "n1",
  nodes: [{ id: "n1", label: "张振国" }],
  edges: [],
};

describe("reduceStreamTurnEvent", () => {
  it("preserves graph_viz on done after graph_viz event", () => {
    let acc = createStreamTurnAccum();
    acc = reduceStreamTurnEvent(acc, { type: "graph_viz", graph: sampleGraph }, "auto");
    acc = reduceStreamTurnEvent(
      acc,
      {
        type: "done",
        answer: "组织关系如下",
        sources: [],
        source_refs: [],
        answer_mode: "kb",
        rag_architecture: "graph",
        verified: true,
      },
      "auto"
    );
    expect(acc.meta?.graph_viz?.nodes).toHaveLength(1);
    expect(acc.meta?.graph_viz?.center_id).toBe("n1");
  });

  it("uses graph_viz from done payload when present", () => {
    let acc = createStreamTurnAccum();
    acc = reduceStreamTurnEvent(
      acc,
      {
        type: "done",
        answer: "ok",
        graph_viz: sampleGraph,
        answer_mode: "kb",
        rag_architecture: "graph",
        verified: true,
      },
      "auto"
    );
    expect(acc.meta?.graph_viz).toEqual(sampleGraph);
  });
});
