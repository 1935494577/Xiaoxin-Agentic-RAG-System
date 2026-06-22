import { describe, it, expect } from "vitest";
import { displayCategoryLabel, displaySlotLabel, PROMPT_SLOT_LABELS } from "../src/lib/promptDisplay";

describe("promptDisplay", () => {
  it("maps builtin slot ids to Chinese labels", () => {
    expect(displaySlotLabel({ id: "kb_task", label: "知识库任务（标准）" })).toBe(
      "知识库任务（标准）"
    );
    expect(displaySlotLabel({ id: "kb_policy", label: "kb_policy" })).toBe(
      PROMPT_SLOT_LABELS.kb_policy
    );
  });

  it("maps categories with numbered Chinese labels", () => {
    expect(displayCategoryLabel("persona")).toContain("角色人设");
    expect(displayCategoryLabel("task")).toContain("任务");
  });
});

describe("adminHelp", () => {
  it("exports feedback workflow steps", async () => {
    const { FEEDBACK_PAGE_HELP } = await import("../src/lib/adminHelp");
    expect(FEEDBACK_PAGE_HELP.steps.length).toBeGreaterThanOrEqual(4);
    expect(FEEDBACK_PAGE_HELP.summary).toMatch(/研判/);
  });
});
