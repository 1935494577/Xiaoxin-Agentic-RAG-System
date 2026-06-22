import { describe, it, expect } from "vitest";
import { messagesToMarkdown } from "../src/lib/exportChatMarkdown";
import type { ChatMessage } from "../src/api/types";

describe("exportChatMarkdown", () => {
  it("formats user and assistant turns with sources", () => {
    const messages: ChatMessage[] = [
      { role: "user", content: "五者是什么？" },
      {
        role: "assistant",
        content: "思者、赢者、学者、德者、行者。",
        meta: { sources: ["data/raw/天赋基础知识.txt"] },
      },
    ];
    const md = messagesToMarkdown(messages, { title: "天赋问答" });
    expect(md).toContain("# 天赋问答");
    expect(md).toContain("## 用户");
    expect(md).toContain("五者是什么？");
    expect(md).toContain("## 助手");
    expect(md).toContain("天赋基础知识.txt");
  });
});
