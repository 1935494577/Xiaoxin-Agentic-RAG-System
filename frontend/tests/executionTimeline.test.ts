import { describe, it, expect } from "vitest";
import {
  applyExecutionStreamEvent,
  buildExecutionSummary,
  labelForStatusPhase,
  stepsFromMessageMeta,
} from "../src/lib/executionTimeline";
import type { StreamEvent } from "../src/api/types";

describe("executionTimeline", () => {
  it("labelForStatusPhase maps known phases", () => {
    expect(labelForStatusPhase("retrieving")).toBe("检索知识库");
    expect(labelForStatusPhase("generating")).toBe("生成回答");
    expect(labelForStatusPhase("unknown_phase")).toBe("unknown_phase");
  });

  it("aggregates status then tool events", () => {
    let steps = applyExecutionStreamEvent([], {
      type: "status",
      phase: "retrieving",
    } as StreamEvent);
    expect(steps).toHaveLength(1);
    expect(steps[0].label).toBe("检索知识库");
    expect(steps[0].pending).toBe(true);

    steps = applyExecutionStreamEvent(steps, {
      type: "status",
      phase: "generating",
      answer_mode: "kb",
      rag_architecture: "classic",
    } as StreamEvent);
    expect(steps).toHaveLength(2);
    expect(steps[0].pending).toBe(false);
    expect(steps[1].label).toBe("生成回答");
    expect(steps[1].pending).toBe(true);

    steps = applyExecutionStreamEvent(steps, {
      type: "tool_call",
      tool: "kb_search",
      arguments: { query: "阅读" },
    } as StreamEvent);
    expect(steps).toHaveLength(3);
    expect(steps[2].kind).toBe("tool");
    expect(steps[2].pending).toBe(true);

    steps = applyExecutionStreamEvent(steps, {
      type: "tool_result",
      tool: "kb_search",
      output: "命中 3 条",
      ok: true,
    } as StreamEvent);
    expect(steps[2].pending).toBe(false);
    expect(steps[2].output).toContain("命中");
  });

  it("buildExecutionSummary counts tools and modes", () => {
    const steps = applyExecutionStreamEvent(
      applyExecutionStreamEvent([], { type: "status", phase: "retrieving" } as StreamEvent),
      { type: "tool_call", tool: "weather", arguments: {} } as StreamEvent
    );
    const summary = buildExecutionSummary(steps, {
      answer_mode: "general",
      rag_architecture: "agentic",
    });
    expect(summary.steps).toBeGreaterThanOrEqual(2);
    expect(summary.tools_used).toContain("weather");
    expect(summary.answer_mode).toBe("general");
    expect(summary.rag_architecture).toBe("agentic");
  });

  it("stepsFromMessageMeta rebuilds tool steps from meta", () => {
    const steps = stepsFromMessageMeta({
      tool_trace: [{ tool: "web_search", output: "ok", ok: true }],
      execution_summary: { steps: 2, tools_used: ["web_search"], answer_mode: "general" },
    });
    expect(steps.some((s) => s.tool === "web_search")).toBe(true);
  });
});
