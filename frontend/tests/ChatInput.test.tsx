/**
 * ChatInput component tests — send/stop behavior, keyboard shortcuts, empty validation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { ChatInput } from "../src/components/chat/ChatInput";

describe("ChatInput", () => {
  const baseProps = {
    value: "",
    onChange: vi.fn(),
    onSend: vi.fn(),
    streaming: false,
    onStop: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders textarea with placeholder", () => {
    render(React.createElement(ChatInput, baseProps));
    expect(screen.getByPlaceholderText("输入问题，助手将基于知识库内容回答")).toBeTruthy();
  });

  it("renders send button disabled when input is empty", () => {
    render(React.createElement(ChatInput, baseProps));
    const btn = screen.getByText("发送");
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });

  it("renders send button enabled when input has text", () => {
    render(React.createElement(ChatInput, { ...baseProps, value: "你好" }));
    const btn = screen.getByText("发送");
    expect((btn as HTMLButtonElement).disabled).toBe(false);
  });

  it("calls onSend when send button clicked with text", async () => {
    const onSend = vi.fn();
    render(React.createElement(ChatInput, { ...baseProps, value: "你好", onSend }));
    await userEvent.click(screen.getByText("发送"));
    expect(onSend).toHaveBeenCalled();
  });

  it("does not call onSend when send button clicked with empty input", async () => {
    const onSend = vi.fn();
    render(React.createElement(ChatInput, { ...baseProps, onSend }));
    await userEvent.click(screen.getByText("发送"));
    expect(onSend).not.toHaveBeenCalled();
  });

  it("calls onSend on Enter (no Shift)", async () => {
    const onSend = vi.fn();
    render(React.createElement(ChatInput, { ...baseProps, value: "问", onSend }));
    const textarea = screen.getByPlaceholderText(/输入问题/);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(onSend).toHaveBeenCalled();
  });

  it("does not call onSend on Shift+Enter", () => {
    const onSend = vi.fn();
    render(React.createElement(ChatInput, { ...baseProps, value: "问", onSend }));
    const textarea = screen.getByPlaceholderText(/输入问题/);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not send when streaming", async () => {
    const onSend = vi.fn();
    render(React.createElement(ChatInput, { ...baseProps, value: "问", onSend, streaming: true }));
    // Enter should not trigger send while streaming
    const textarea = screen.getByPlaceholderText(/输入问题/);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("shows stop button instead of send when streaming", () => {
    render(React.createElement(ChatInput, { ...baseProps, streaming: true }));
    expect(screen.getByText("停止")).toBeTruthy();
    expect(screen.queryByText("发送")).toBeNull();
  });

  it("calls onStop when stop button clicked", async () => {
    const onStop = vi.fn();
    render(React.createElement(ChatInput, { ...baseProps, streaming: true, onStop }));
    await userEvent.click(screen.getByText("停止"));
    expect(onStop).toHaveBeenCalled();
  });

  it("textarea is disabled when streaming", () => {
    render(React.createElement(ChatInput, { ...baseProps, streaming: true }));
    const textarea = screen.getByPlaceholderText(/输入问题/) as HTMLTextAreaElement;
    expect(textarea.disabled).toBe(true);
  });

  it("calls onChange when user types", async () => {
    const onChange = vi.fn();
    render(React.createElement(ChatInput, { ...baseProps, onChange }));
    const textarea = screen.getByPlaceholderText(/输入问题/);
    await userEvent.type(textarea, "你好");
    expect(onChange).toHaveBeenCalled();
  });

  it("strips whitespace-only input (does not send spaces only)", () => {
    const onSend = vi.fn();
    render(React.createElement(ChatInput, { ...baseProps, value: "   ", onSend }));
    const textarea = screen.getByPlaceholderText(/输入问题/);
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("renders custom placeholder when provided", () => {
    render(React.createElement(ChatInput, { ...baseProps, placeholder: "自定义占位符" }));
    expect(screen.getByPlaceholderText("自定义占位符")).toBeTruthy();
  });
});
