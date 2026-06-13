import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChatToolbar } from "../src/components/chat/ChatToolbar";

describe("ChatToolbar", () => {
  it("shows hint when new topic pending", () => {
    render(
      <ChatToolbar
        hybridExpert={true}
        onHybridChange={vi.fn()}
        newTopicPending={true}
        onNewTopicToggle={vi.fn()}
        streaming={false}
      />
    );
    expect(screen.getByText(/已开启/)).toBeTruthy();
    expect(screen.getByText("下一条：新话题")).toBeTruthy();
  });

  it("toggles new topic button", () => {
    const onToggle = vi.fn();
    render(
      <ChatToolbar
        hybridExpert={false}
        onHybridChange={vi.fn()}
        newTopicPending={false}
        onNewTopicToggle={onToggle}
        streaming={false}
      />
    );
    fireEvent.click(screen.getByText("新话题"));
    expect(onToggle).toHaveBeenCalled();
  });
});
