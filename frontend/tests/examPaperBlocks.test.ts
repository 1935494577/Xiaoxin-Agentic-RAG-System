import { describe, it, expect } from "vitest";
import {
  collectExamCandidateBlocks,
  collectExamPaperBlocks,
  parseExamCandidateFences,
  parseExamPaperFences,
  stripExamPaperFences,
} from "../src/lib/examPaperBlocks";

describe("examPaperBlocks", () => {
  it("parses exam_paper fence", () => {
    const md = `已加载卷面。\n\n\`\`\`exam_paper\n{"source_paper_id":"abc-123","title":"样卷"}\n\`\`\`\n\n点击开始答题。`;
    const blocks = parseExamPaperFences(md);
    expect(blocks).toHaveLength(1);
    expect(blocks[0].source_paper_id).toBe("abc-123");
    expect(stripExamPaperFences(md)).not.toContain("abc-123");
  });

  it("merges meta ui_blocks with fences without dup", () => {
    const md = "```exam_paper\n{\"source_paper_id\":\"x1\"}\n```";
    const blocks = collectExamPaperBlocks(md, [
      { type: "exam_paper", source_paper_id: "x1", title: "A" },
      { type: "exam_paper", source_paper_id: "x2" },
    ]);
    expect(blocks.map((b) => b.source_paper_id)).toEqual(["x1", "x2"]);
  });

  it("parses exam_candidates fence", () => {
    const md = `\`\`\`exam_candidates\n{"items":[{"id":"a","title":"卷A"},{"id":"b","title":"卷B"}]}\n\`\`\``;
    const blocks = parseExamCandidateFences(md);
    expect(blocks).toHaveLength(1);
    expect(blocks[0].items.map((i) => i.id)).toEqual(["a", "b"]);
    expect(stripExamPaperFences(md)).toBe("");
  });

  it("collects candidates from meta", () => {
    const blocks = collectExamCandidateBlocks("hello", [
      {
        type: "exam_candidates",
        items: [{ id: "p1", title: "高考卷" }],
      },
    ]);
    expect(blocks[0].items[0].id).toBe("p1");
  });
});
