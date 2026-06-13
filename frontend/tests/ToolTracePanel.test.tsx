import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ToolTracePanel } from "../src/components/chat/ToolTracePanel";

describe("ToolTracePanel", () => {
  it("shows short tool output expanded", () => {
    render(
      <ToolTracePanel
        items={[
          {
            tool: "get_beijing_time",
            output: "北京时间：2026年06月13日 15:13:01",
            ok: true,
          },
        ]}
      />
    );
    expect(screen.getByText(/北京时间/)).toBeTruthy();
  });

  it("collapses long tool output by default", () => {
    const long = "搜索「端午节」结果：\n\n" + "详细内容".repeat(80);
    render(
      <ToolTracePanel
        items={[{ tool: "web_search", arguments: { query: "端午节" }, output: long, ok: true }]}
      />
    );
    expect(screen.getByText(/web_search/)).toBeTruthy();
    expect(screen.getByText(new RegExp(`${long.length} 字`))).toBeTruthy();
    expect(screen.queryByText(long)).toBeNull();
  });

  it("expands long output on click", () => {
    const long = "A".repeat(200);
    render(
      <ToolTracePanel items={[{ tool: "web_search", output: long, ok: true }]} />
    );
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText(long)).toBeTruthy();
  });
});
