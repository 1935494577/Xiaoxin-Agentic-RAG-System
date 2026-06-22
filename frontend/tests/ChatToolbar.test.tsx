import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChatToolbar } from "../src/components/chat/ChatToolbar";

const baseProps = {
  hybridExpert: true,
  onHybridChange: vi.fn(),
  newTopicPending: false,
  onNewTopicToggle: vi.fn(),
  streaming: false,
};

describe("ChatToolbar", () => {
  it("shows hint when new topic pending", () => {
    render(<ChatToolbar {...baseProps} newTopicPending={true} />);
    expect(screen.getByText(/已开启/)).toBeTruthy();
    expect(screen.getByText("下一条：新话题")).toBeTruthy();
  });

  it("toggles new topic button", () => {
    const onToggle = vi.fn();
    render(<ChatToolbar {...baseProps} hybridExpert={false} onNewTopicToggle={onToggle} />);
    fireEvent.click(screen.getByText("新话题"));
    expect(onToggle).toHaveBeenCalled();
  });

  it("does not expose RAG architecture controls", () => {
    render(<ChatToolbar {...baseProps} />);
    expect(screen.queryByText("架构")).toBeNull();
    expect(screen.queryByText("任务")).toBeNull();
    expect(screen.queryByText("来源")).toBeNull();
    expect(screen.queryByText("临时文档")).toBeNull();
  });
});
