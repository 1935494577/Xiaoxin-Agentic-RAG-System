/**
 * ProcessingPage component test.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("../src/api/client", () => ({
  fetchProcessingTools: vi.fn(),
  saveProcessingTools: vi.fn(),
  fetchAgentTools: vi.fn(),
  saveAgentTools: vi.fn(),
}));

import ProcessingPage from "../src/pages/admin/ProcessingPage";
import * as client from "../src/api/client";

function wrapper(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, ui);
}

describe("ProcessingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(client.fetchAgentTools).mockResolvedValue({
      chat_tools_enabled: true,
      tools: [{ id: "get_weather", label: "天气查询", description: "查天气", enabled: true }],
    });
  });

  it("renders ingest tab by default", async () => {
    vi.mocked(client.fetchProcessingTools).mockReturnValue(new Promise(() => {}));

    render(wrapper(React.createElement(ProcessingPage)));
    expect(screen.getByText("入库工具")).toBeTruthy();
    expect(screen.getByText("对话工具")).toBeTruthy();
    expect(screen.getByText("加载中...")).toBeTruthy();
  });

  it("shows ingest tools from API", async () => {
    vi.mocked(client.fetchProcessingTools).mockResolvedValue({
      tools: [
        { id: "tool_a", label: "解析器A", description: "", enabled: true },
        { id: "tool_b", label: "脱敏工具B", description: "", enabled: false },
      ],
      use_llm_router: true,
    });

    render(wrapper(React.createElement(ProcessingPage)));

    await waitFor(() => {
      expect(screen.getByText("启用大模型选工具（LangChain bind_tools）")).toBeTruthy();
    });
    expect(screen.getByText("解析器A")).toBeTruthy();
    expect(screen.getByText("脱敏工具B")).toBeTruthy();
  });

  it("switches to agent tools tab", async () => {
    vi.mocked(client.fetchProcessingTools).mockResolvedValue({
      tools: [{ id: "t1", label: "工具1", description: "", enabled: true }],
      use_llm_router: false,
    });

    render(wrapper(React.createElement(ProcessingPage)));

    await waitFor(() => {
      expect(screen.getByText("工具1")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("对话工具"));

    await waitFor(() => {
      expect(screen.getByText("启用对话工具（function calling）")).toBeTruthy();
    });
    expect(screen.getByText("天气查询")).toBeTruthy();
    expect(screen.getByText("get_weather")).toBeTruthy();
  });
});
