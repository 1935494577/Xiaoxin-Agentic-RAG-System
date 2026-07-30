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

  it("captures exam_paper ui_block from present_exam_paper tool_result", () => {
    let acc = createStreamTurnAccum();
    acc = reduceStreamTurnEvent(
      acc,
      {
        type: "tool_result",
        tool: "present_exam_paper",
        ok: true,
        output: JSON.stringify({
          ok: true,
          ui_block: {
            type: "exam_paper",
            source_paper_id: "sp-1",
            title: "样卷",
          },
        }),
      },
      "auto"
    );
    acc = reduceStreamTurnEvent(
      acc,
      {
        type: "done",
        answer: "请开始答题",
        answer_mode: "general",
        verified: true,
      },
      "auto"
    );
    expect(acc.meta?.ui_blocks?.[0]?.source_paper_id).toBe("sp-1");
  });

  it("captures exam_candidates from search_exam_papers tool_result", () => {
    let acc = createStreamTurnAccum();
    acc = reduceStreamTurnEvent(
      acc,
      {
        type: "tool_result",
        tool: "search_exam_papers",
        ok: true,
        output: JSON.stringify({
          ok: true,
          ui_block: {
            type: "exam_candidates",
            items: [
              { id: "a", title: "卷A" },
              { id: "b", title: "卷B" },
            ],
          },
        }),
      },
      "auto"
    );
    expect(acc.meta?.ui_blocks?.[0]?.type).toBe("exam_candidates");
    expect(acc.meta?.ui_blocks?.[0]?.items).toHaveLength(2);
  });

  it("keeps ui_blocks from done.exam_bank gate", () => {
    let acc = createStreamTurnAccum();
    acc = reduceStreamTurnEvent(
      acc,
      {
        type: "done",
        answer: "已从题库找到",
        answer_mode: "exam_bank",
        verified: true,
        ui_blocks: [
          { type: "exam_paper", source_paper_id: "gate-1", title: "浙江卷" },
        ],
      },
      "task"
    );
    expect(acc.meta?.ui_blocks?.[0]?.source_paper_id).toBe("gate-1");
    expect(acc.meta?.answer_mode).toBe("exam_bank");
  });
});
