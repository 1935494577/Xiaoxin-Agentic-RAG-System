/**
 * MessageBubble component tests — rendering, markdown, citations, feedback, streaming cursor.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// Mock useAuth to provide stable userId
vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({ userId: "test_user_id" }),
}));

// Mock submitFeedback
const mockSubmitFeedback = vi.fn();
vi.mock("../src/api/client", () => ({
  submitFeedback: (...args: unknown[]) => mockSubmitFeedback(...args),
}));

// Mock LottiePlayer to avoid DotLottie canvas init in jsdom
vi.mock("../src/components/chat/LottiePlayer", () => ({
  default: ({ className }: { className?: string }) => {
    const React = require("react");
    return React.createElement("div", { className, "data-testid": "lottie-player" });
  },
}));

import MessageBubble from "../src/components/chat/MessageBubble";

describe("MessageBubble", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitFeedback.mockResolvedValue(undefined);
  });

  it("renders user message with avatar initial", () => {
    const msg = { role: "user" as const, content: "用户的问题" };
    render(
      React.createElement(MessageBubble, {
        message: msg,
        userDisplayName: "小明",
      })
    );
    expect(screen.getByText("小")).toBeTruthy();
    expect(screen.getByText("用户的问题")).toBeTruthy();
  });

  it("renders assistant message with AI avatar", () => {
    const msg = { role: "assistant" as const, content: "助手的回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByText("AI")).toBeTruthy();
    expect(screen.getByText("助手的回答")).toBeTruthy();
  });

  it("renders assistant with custom name initial", () => {
    const msg = { role: "assistant" as const, content: "回答" };
    render(
      React.createElement(MessageBubble, {
        message: msg,
        aiDisplayName: "小脑",
      })
    );
    expect(screen.getByText("小")).toBeTruthy();
  });

  it("renders markdown in assistant message", () => {
    const msg = { role: "assistant" as const, content: "**粗体** _斜体_" };
    render(React.createElement(MessageBubble, { message: msg }));
    // ReactMarkdown renders <strong> and <em>
    const strong = document.querySelector("strong");
    expect(strong).toBeTruthy();
    expect(strong?.textContent).toBe("粗体");
  });

  it("shows kb badge when answer_mode is kb", () => {
    const msg = {
      role: "assistant" as const,
      content: "回答",
      meta: { answer_mode: "kb" as const, sources: ["doc.pdf"] },
    };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByText("知识库回答")).toBeTruthy();
  });

  it("shows general badge when answer_mode is general", () => {
    const msg = {
      role: "assistant" as const,
      content: "通用回答",
      meta: { answer_mode: "general" as const },
    };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getAllByText("通用回答").length).toBeGreaterThanOrEqual(1);
  });

  it("shows source citations in assistant message", () => {
    const msg = {
      role: "assistant" as const,
      content: "带引用的回答",
      meta: { sources: ["doc1.pdf", "doc2.md"] },
    };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByText("引用来源")).toBeTruthy();
    expect(screen.getByText(/doc1.pdf/)).toBeTruthy();
    expect(screen.getByText(/doc2.md/)).toBeTruthy();
  });

  it("renders citations as chips with file icon", () => {
    const msg = {
      role: "assistant" as const,
      content: "带引用的回答",
      meta: {
        source_refs: [{ parent_id: "p1", source: "docs/制度手册.pdf" }],
      },
    };
    render(React.createElement(MessageBubble, { message: msg }));
    const chip = screen.getByRole("button", { name: /制度手册\.pdf/ });
    expect(chip.className).toContain("border");
    expect(chip.className).toContain("rounded-lg");
    expect(chip.querySelector("svg")).toBeTruthy();
  });

  it("strips footnote citations from displayed content", () => {
    const msg = {
      role: "assistant" as const,
      content: "回答内容\n\n引用：file.pdf; doc.md",
    };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.queryByText(/引用：/)).toBeNull();
    // The main text is rendered
    expect(screen.getByText("回答内容")).toBeTruthy();
  });

  it("does not render tool trace details in chat", () => {
    const msg = {
      role: "assistant" as const,
      content: "今日财报速览",
      meta: {
        tool_trace: [
          {
            tool: "web_search",
            arguments: { query: "今日财报" },
            output: "搜索「今日财报」结果：\n1. Tesla\n   链接: https://example.com/tesla",
            ok: true,
          },
        ],
      },
    };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.queryByText(/web_search/)).toBeNull();
    expect(screen.queryByText(/搜索「今日财报」/)).toBeNull();
    expect(screen.getByText("今日财报速览")).toBeTruthy();
  });

  it("shows feedback buttons for assistant messages (not streaming)", () => {
    const msg = { role: "assistant" as const, content: "回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByRole("button", { name: "有帮助" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "没帮助" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "复制回答" })).toBeTruthy();
  });

  it("reveals action row on message hover (group-hover)", () => {
    const msg = { role: "assistant" as const, content: "回答" };
    const { container } = render(React.createElement(MessageBubble, { message: msg }));
    const group = container.querySelector(".group");
    expect(group).toBeTruthy();
    const actionRow = screen.getByRole("button", { name: "复制回答" }).parentElement;
    expect(actionRow?.className).toContain("group-hover:opacity-100");
  });

  it("copies answer and shows copied state", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const msg = { role: "assistant" as const, content: "要复制的回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    fireEvent.click(screen.getByRole("button", { name: "复制回答" }));
    expect(writeText).toHaveBeenCalledWith("要复制的回答");
    await waitFor(() => {
      expect(screen.getByText("已复制")).toBeTruthy();
    });
  });

  it("hides feedback buttons when streaming", () => {
    const msg = { role: "assistant" as const, content: "部分" };
    render(React.createElement(MessageBubble, { message: msg, streaming: true }));
    expect(screen.queryByRole("button", { name: "有帮助" })).toBeNull();
    expect(screen.queryByRole("button", { name: "没帮助" })).toBeNull();
    expect(screen.queryByRole("button", { name: "复制回答" })).toBeNull();
  });

  it("calls submitFeedback on thumbs up", async () => {
    mockSubmitFeedback.mockResolvedValue(undefined);
    const msg = {
      role: "assistant" as const,
      content: "回答",
      meta: { trace_id: "trace_123" },
    };
    render(React.createElement(MessageBubble, { message: msg }));
    fireEvent.click(screen.getByRole("button", { name: "有帮助" }));
    expect(mockSubmitFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        user_id: "test_user_id",
        rating: 1,
        trace_id: "trace_123",
        message_id: "trace_123",
      })
    );
  });

  it("shows correction form on thumbs down and submits on skip", async () => {
    mockSubmitFeedback.mockResolvedValue(undefined);
    const msg = { role: "assistant" as const, content: "回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    fireEvent.click(screen.getByRole("button", { name: "没帮助" }));
    expect(screen.getByPlaceholderText(/例如/)).toBeTruthy();
    fireEvent.click(screen.getByText("跳过"));
    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith(
        expect.objectContaining({
          user_id: "test_user_id",
          rating: 0,
        })
      );
    });
  });

  it("submits correction text with negative feedback", async () => {
    mockSubmitFeedback.mockResolvedValue(undefined);
    const msg = { role: "assistant" as const, content: "回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    fireEvent.click(screen.getByRole("button", { name: "没帮助" }));
    fireEvent.change(screen.getByPlaceholderText(/例如/), {
      target: { value: "制度已过期" },
    });
    fireEvent.click(screen.getByText("提交反馈"));
    await waitFor(() => {
      expect(mockSubmitFeedback).toHaveBeenCalledWith(
        expect.objectContaining({
          rating: 0,
          correction: "制度已过期",
        })
      );
    });
  });

  it("prevents duplicate feedback (buttons disabled after click)", async () => {
    mockSubmitFeedback.mockResolvedValue(undefined);
    const msg = { role: "assistant" as const, content: "回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    fireEvent.click(screen.getByRole("button", { name: "有帮助" }));
    await waitFor(() => {
      expect((screen.getByRole("button", { name: "有帮助" }) as HTMLButtonElement).disabled).toBe(true);
    });
    expect((screen.getByRole("button", { name: "没帮助" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "有帮助" }));
    expect(mockSubmitFeedback).toHaveBeenCalledTimes(1);
  });

  it("reverts feedback on API failure", async () => {
    mockSubmitFeedback.mockRejectedValue(new Error("Network error"));
    const msg = { role: "assistant" as const, content: "回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    fireEvent.click(screen.getByRole("button", { name: "有帮助" }));
    await waitFor(() => {
      expect((screen.getByRole("button", { name: "有帮助" }) as HTMLButtonElement).disabled).toBe(false);
    });
  });

  it("renders streaming as plain text (not markdown parse)", () => {
    const msg = { role: "assistant" as const, content: "正在输入**未解析**" };
    render(React.createElement(MessageBubble, { message: msg, streaming: true }));
    expect(screen.getByText(/正在输入\*\*未解析\*\*/)).toBeTruthy();
    expect(document.querySelector("strong")).toBeNull();
  });

  it("shows LottiePlayer + '思考中' for empty content while streaming", () => {
    const msg = { role: "assistant" as const, content: "" };
    render(React.createElement(MessageBubble, { message: msg, streaming: true }));
    // Streaming + empty => Lottie animation + 思考中 text
    expect(screen.getByText("思考中")).toBeTruthy();
    expect(screen.getByTestId("lottie-player")).toBeTruthy();
  });

  it("shows ellipsis for assistant with no content and not streaming", () => {
    const msg = { role: "assistant" as const, content: "" };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByText("…")).toBeTruthy();
  });
});
