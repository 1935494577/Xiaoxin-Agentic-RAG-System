import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ExecutionTimeline } from "../src/components/chat/ExecutionTimeline";
import type { ExecutionStep } from "../src/lib/executionTimeline";

const sampleSteps: ExecutionStep[] = [
  { id: "s1", kind: "status", label: "检索知识库", pending: false },
  {
    id: "t1",
    kind: "tool",
    label: "kb_search",
    tool: "kb_search",
    output: "3 条结果",
    ok: true,
    pending: false,
  },
  { id: "s2", kind: "status", label: "生成回答", pending: true },
];

describe("ExecutionTimeline", () => {
  it("renders collapsed summary when not live", () => {
    render(<ExecutionTimeline steps={sampleSteps} live={false} />);
    expect(screen.getByText(/执行步骤/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /执行步骤/ }));
    expect(screen.getByText("检索知识库")).toBeTruthy();
    expect(screen.getByText("kb_search")).toBeTruthy();
  });

  it("expands automatically while streaming", () => {
    render(<ExecutionTimeline steps={sampleSteps} live />);
    expect(screen.getByText("检索知识库")).toBeTruthy();
    expect(screen.getByText("执行中…")).toBeTruthy();
  });

  it("returns null when no steps", () => {
    const { container } = render(<ExecutionTimeline steps={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
