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

import MessageBubble from "../src/components/chat/MessageBubble";

describe("MessageBubble", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitFeedback.mockResolvedValue(undefined);
  });

  it("renders user message with '你' avatar", () => {
    const msg = { role: "user" as const, content: "用户的问题" };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByText("你")).toBeTruthy();
    expect(screen.getByText("用户的问题")).toBeTruthy();
  });

  it("renders assistant message with 'AI' avatar", () => {
    const msg = { role: "assistant" as const, content: "助手的回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByText("AI")).toBeTruthy();
    expect(screen.getByText("助手的回答")).toBeTruthy();
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
    expect(screen.getByText("引用")).toBeTruthy();
    expect(screen.getByText(/doc1.pdf/)).toBeTruthy();
    expect(screen.getByText(/doc2.md/)).toBeTruthy();
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

  it("shows feedback buttons for assistant messages (not streaming)", () => {
    const msg = { role: "assistant" as const, content: "回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByText("👍")).toBeTruthy();
    expect(screen.getByText("👎")).toBeTruthy();
    expect(screen.getByText("复制")).toBeTruthy();
  });

  it("hides feedback buttons when streaming", () => {
    const msg = { role: "assistant" as const, content: "部分" };
    render(React.createElement(MessageBubble, { message: msg, streaming: true }));
    expect(screen.queryByText("👍")).toBeNull();
    expect(screen.queryByText("👎")).toBeNull();
    expect(screen.queryByText("复制")).toBeNull();
  });

  it("calls submitFeedback on thumbs up", async () => {
    mockSubmitFeedback.mockResolvedValue(undefined);
    const msg = {
      role: "assistant" as const,
      content: "回答",
      meta: { trace_id: "trace_123" },
    };
    render(React.createElement(MessageBubble, { message: msg }));
    fireEvent.click(screen.getByText("👍"));
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
    fireEvent.click(screen.getByText("👎"));
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
    fireEvent.click(screen.getByText("👎"));
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
    fireEvent.click(screen.getByText("👍"));
    await waitFor(() => {
      expect((screen.getByText("👍") as HTMLButtonElement).disabled).toBe(true);
    });
    expect((screen.getByText("👎") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByText("👍"));
    expect(mockSubmitFeedback).toHaveBeenCalledTimes(1);
  });

  it("reverts feedback on API failure", async () => {
    mockSubmitFeedback.mockRejectedValue(new Error("Network error"));
    const msg = { role: "assistant" as const, content: "回答" };
    render(React.createElement(MessageBubble, { message: msg }));
    fireEvent.click(screen.getByText("👍"));
    await waitFor(() => {
      expect((screen.getByText("👍") as HTMLButtonElement).disabled).toBe(false);
    });
  });

  it("renders streaming cursor indicator", () => {
    const msg = { role: "assistant" as const, content: "正在输入" };
    render(React.createElement(MessageBubble, { message: msg, streaming: true }));
    // Cursor is CSS-only (after:content['▋']) — just verify no crash
    expect(screen.getByText("正在输入")).toBeTruthy();
  });

  it("shows '…' thinking indicator for assistant with no content while streaming", () => {
    const msg = { role: "assistant" as const, content: "" };
    render(React.createElement(MessageBubble, { message: msg, streaming: true }));
    // Streaming + empty => show "…" to indicate AI is thinking
    expect(screen.getByText("…")).toBeTruthy();
  });

  it("shows ellipsis for assistant with no content and not streaming", () => {
    const msg = { role: "assistant" as const, content: "" };
    render(React.createElement(MessageBubble, { message: msg }));
    expect(screen.getByText("…")).toBeTruthy();
  });
});
