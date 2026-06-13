import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarkdownContent, StreamingPlainText } from "../src/components/chat/MarkdownContent";

describe("MarkdownContent", () => {
  it("renders headings and lists", () => {
    render(<MarkdownContent content={"## 标题\n\n- 要点一\n- 要点二"} />);
    expect(screen.getByRole("heading", { level: 2, name: "标题" })).toBeTruthy();
    expect(screen.getByText("要点一")).toBeTruthy();
    expect(screen.getByText("要点二")).toBeTruthy();
  });

  it("renders markdown table", () => {
    render(<MarkdownContent content={"| A | B |\n| --- | --- |\n| 1 | 2 |"} />);
    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.getByText("1")).toBeTruthy();
  });
});

describe("StreamingPlainText", () => {
  it("shows plain text with cursor element", () => {
    const { container } = render(<StreamingPlainText content="正在输入" />);
    expect(screen.getByText("正在输入")).toBeTruthy();
    expect(container.querySelector(".stream-cursor")).toBeTruthy();
  });
});
