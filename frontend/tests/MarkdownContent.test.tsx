import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarkdownContent, StreamingPlainText } from "../src/components/chat/MarkdownContent";
import {
  hasMathDelimiters,
  hasLooseLatex,
  needsMathRender,
  normalizeLooseParenLatex,
  prepareMathMarkdown,
} from "../src/lib/mathDelimiters";

describe("mathDelimiters", () => {
  it("detects $ and $$ delimiters", () => {
    expect(hasMathDelimiters("面积为 $x^2$")).toBe(true);
    expect(hasMathDelimiters("$$\\frac{1}{2}$$")).toBe(true);
    expect(hasMathDelimiters("普通中文无公式")).toBe(false);
  });

  it("detects \\( \\) and \\[ \\]", () => {
    expect(hasMathDelimiters("令 \\(a+b=1\\)")).toBe(true);
    expect(hasMathDelimiters("\\[x=1\\]")).toBe(true);
  });

  it("detects loose LaTeX commands without delimiters", () => {
    expect(hasLooseLatex("( \\vec{a}=(0,1) )")).toBe(true);
    expect(hasLooseLatex("价格 100 元")).toBe(false);
  });

  it("needsMathRender is false for plain prose", () => {
    expect(needsMathRender("今天天气不错，请查制度第3条。")).toBe(false);
  });

  it("normalizeLooseParenLatex wraps backslash groups", () => {
    const out = normalizeLooseParenLatex("若 ( \\bar{z} = ) 则选");
    expect(out).toContain("$\\bar{z} =$");
    expect(prepareMathMarkdown("无公式")).toBe("无公式");
  });
});

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

  it("does not inject katex for plain text", () => {
    const { container } = render(<MarkdownContent content="请参阅员工手册第三章。" />);
    expect(container.querySelector(".katex")).toBeNull();
  });

  it("renders inline math with katex when delimiters present", () => {
    const { container } = render(<MarkdownContent content={"已知 $x^2=4$，求 $x$"} />);
    expect(container.querySelector(".katex")).toBeTruthy();
  });
});

describe("StreamingPlainText", () => {
  it("shows plain text with cursor element", () => {
    const { container } = render(<StreamingPlainText content="正在输入" />);
    expect(screen.getByText("正在输入")).toBeTruthy();
    expect(container.querySelector(".stream-cursor")).toBeTruthy();
  });
});
