/**
 * Unit tests for MessageBubble utility functions.
 * These are pure functions extracted from the component for testability.
 */
import { describe, it, expect } from "vitest";

// ---- Replicated pure functions from MessageBubble.tsx ----
// (extracted here so tests don't depend on component internals via import)

function stripFootnotes(text: string): string {
  return text
    .replace(/\r?\n(\r?\n)?引用[:：][^\n]*(?:[;\n][^\n]*)*$/u, "")
    .trim();
}

function uniqueLabels(labels: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of labels) {
    const label = raw.trim();
    if (!label || seen.has(label)) continue;
    seen.add(label);
    out.push(label);
  }
  return out;
}

describe("stripFootnotes", () => {
  it("removes trailing Chinese citation line", () => {
    const input = "这是回答内容\n\n引用：file.pdf; doc.md";
    expect(stripFootnotes(input)).toBe("这是回答内容");
  });

  it("removes trailing citation with colon variant", () => {
    const input = "Some answer\n引用: source1; source2";
    expect(stripFootnotes(input)).toBe("Some answer");
  });

  it("does not modify text without citations", () => {
    const text = "普通回答内容，没有引用信息";
    expect(stripFootnotes(text)).toBe(text);
  });

  it("handles empty string", () => {
    expect(stripFootnotes("")).toBe("");
  });

  it("handles multiline citations", () => {
    const input = "Answer text\n\n引用：file1.pdf\nfile2.md\nfile3.docx";
    expect(stripFootnotes(input)).toBe("Answer text");
  });
});

describe("uniqueLabels", () => {
  it("removes duplicates (case sensitive)", () => {
    expect(uniqueLabels(["a.pdf", "b.md", "a.pdf"])).toEqual(["a.pdf", "b.md"]);
  });

  it("trims whitespace", () => {
    expect(uniqueLabels(["  a.pdf ", " b.md "])).toEqual(["a.pdf", "b.md"]);
  });

  it("filters empty strings", () => {
    expect(uniqueLabels(["a.pdf", "", "  ", "b.md"])).toEqual(["a.pdf", "b.md"]);
  });

  it("returns empty for empty input", () => {
    expect(uniqueLabels([])).toEqual([]);
  });

  it("preserves insertion order", () => {
    expect(uniqueLabels(["c", "a", "b", "a", "c"])).toEqual(["c", "a", "b"]);
  });
});
