/**
 * SessionList component tests — rendering, selection, CRUD callbacks, department selector.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { SessionList } from "../src/components/chat/SessionList";
import type { ChatSession } from "../src/api/types";

function makeSession(id: string, title: string): ChatSession {
  return { id, title, updated_at: "2025-01-01" };
}

describe("SessionList", () => {
  const baseProps = {
    sessions: [] as ChatSession[],
    activeId: null as string | null,
    onSelect: vi.fn(),
    onNew: vi.fn(),
    onDelete: vi.fn(),
    department: "general",
    onDepartment: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Jnao Chat header", () => {
    render(React.createElement(SessionList, baseProps));
    expect(screen.getByText("Jnao Chat")).toBeTruthy();
  });

  it("renders new and delete buttons", () => {
    render(React.createElement(SessionList, baseProps));
    expect(screen.getByText("新建")).toBeTruthy();
    expect(screen.getByText("删除")).toBeTruthy();
  });

  it("delete button is disabled when no activeId", () => {
    render(React.createElement(SessionList, { ...baseProps, activeId: null }));
    expect((screen.getByText("删除") as HTMLButtonElement).disabled).toBe(true);
  });

  it("delete button is enabled when activeId is set", () => {
    render(React.createElement(SessionList, { ...baseProps, activeId: "s1" }));
    expect((screen.getByText("删除") as HTMLButtonElement).disabled).toBe(false);
  });

  it("calls onNew when new button clicked", async () => {
    const onNew = vi.fn();
    render(React.createElement(SessionList, { ...baseProps, onNew }));
    await userEvent.click(screen.getByText("新建"));
    expect(onNew).toHaveBeenCalled();
  });

  it("calls onDelete when delete button clicked with activeId", async () => {
    const onDelete = vi.fn();
    render(React.createElement(SessionList, { ...baseProps, activeId: "s1", onDelete }));
    await userEvent.click(screen.getByText("删除"));
    expect(onDelete).toHaveBeenCalled();
  });

  it("renders session items with titles", () => {
    const sessions = [makeSession("s1", "对话一"), makeSession("s2", "对话二")];
    render(React.createElement(SessionList, { ...baseProps, sessions }));
    expect(screen.getByText("对话一")).toBeTruthy();
    expect(screen.getByText("对话二")).toBeTruthy();
  });

  it("shows '新对话' for sessions without title", () => {
    const sessions = [makeSession("s1", "")];
    render(React.createElement(SessionList, { ...baseProps, sessions }));
    expect(screen.getByText("新对话")).toBeTruthy();
  });

  it("calls onSelect when session is clicked", async () => {
    const onSelect = vi.fn();
    const sessions = [makeSession("s1", "对话一")];
    render(React.createElement(SessionList, { ...baseProps, sessions, onSelect }));
    await userEvent.click(screen.getByText("对话一"));
    expect(onSelect).toHaveBeenCalledWith("s1");
  });

  it("highlights active session with brand color", () => {
    const sessions = [makeSession("s1", "对话一"), makeSession("s2", "对话二")];
    const { container } = render(
      React.createElement(SessionList, { ...baseProps, sessions, activeId: "s1" })
    );
    const activeBtn = screen.getByText("对话一").closest("button");
    const inactiveBtn = screen.getByText("对话二").closest("button");
    expect(activeBtn?.className).toContain("bg-brand-light");
    expect(inactiveBtn?.className).not.toContain("bg-brand-light");
  });

  it("renders department selector with all options", () => {
    render(React.createElement(SessionList, baseProps));
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("general");
    expect(screen.getByText("技术")).toBeTruthy();
    expect(screen.getByText("市场")).toBeTruthy();
    expect(screen.getByText("人事")).toBeTruthy();
    expect(screen.getByText("财务")).toBeTruthy();
  });

  it("calls onDepartment when department changed", () => {
    const onDepartment = vi.fn();
    render(React.createElement(SessionList, { ...baseProps, onDepartment }));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "技术" } });
    expect(onDepartment).toHaveBeenCalledWith("技术");
  });

  it("renders empty session list gracefully", () => {
    render(React.createElement(SessionList, baseProps));
    // No session items rendered — no crash
    expect(screen.getByText("新建")).toBeTruthy();
  });

  it("renders many sessions without performance issues", () => {
    const sessions = Array.from({ length: 50 }, (_, i) => makeSession(`s${i}`, `对话${i}`));
    render(React.createElement(SessionList, { ...baseProps, sessions }));
    expect(screen.getByText("对话0")).toBeTruthy();
    expect(screen.getByText("对话49")).toBeTruthy();
  });
});
