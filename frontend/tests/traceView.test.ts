import { describe, it, expect } from "vitest";
import { parseFeedbackTrace } from "../src/lib/traceView";

describe("parseFeedbackTrace", () => {
  it("parses spans into Chinese labels", () => {
    const view = parseFeedbackTrace({
      trace_id: "abc123",
      question: "超脑阅读要求是什么？",
      answer_mode: "kb",
      started_at: "2026-06-16T08:00:00.000Z",
      ended_at: "2026-06-16T08:00:02.500Z",
      user_id: "u1",
      meta: { rag_architecture: "classic", source_count: 2 },
      spans: [
        {
          type: "retrieval",
          name: "retriever",
          status: "ok",
          latency_ms: 120,
          input: { question: "超脑阅读要求是什么？", stream_fast_mode: true },
          output: {
            result: {
              rewritten_query: "超脑阅读 要求",
              context_count: 3,
              rag_architecture: "classic",
              contexts_meta: [{ source: "docs/training/超脑阅读.pdf" }],
            },
          },
        },
        {
          type: "router",
          name: "chain",
          status: "ok",
          latency_ms: 5,
          output: { result: { answer_mode: "kb", rag_architecture: "classic" } },
        },
        {
          type: "llm_call",
          name: "llm",
          status: "ok",
          latency_ms: 800,
          input: { model: "gpt-4o-mini", answer_mode: "kb" },
        },
      ],
    });

    expect(view.traceId).toBe("abc123");
    expect(view.answerModeLabel).toBe("知识库");
    expect(view.contextCount).toBe(3);
    expect(view.sources).toContain("超脑阅读.pdf");
    expect(view.spans[0]?.label).toContain("知识库检索");
    expect(view.spans[1]?.label).toContain("判定回答路径");
    expect(view.durationLabel).toMatch(/秒|毫秒/);
  });
});
