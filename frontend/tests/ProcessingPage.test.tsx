/**
 * ProcessingPage component test.
 * Verifies that tool data from API correctly initializes the form (useEffect, not useState bug).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock API client
vi.mock("../src/api/client", () => ({
  fetchProcessingTools: vi.fn(),
  saveProcessingTools: vi.fn(),
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
  });

  it("renders loading state initially", () => {
    vi.mocked(client.fetchProcessingTools).mockReturnValue(new Promise(() => {})); // never resolves

    render(wrapper(React.createElement(ProcessingPage)));
    expect(screen.getByText("加载中...")).toBeTruthy();
  });

  it("shows error when API fails", async () => {
    vi.mocked(client.fetchProcessingTools).mockRejectedValue(new Error("API down"));

    render(wrapper(React.createElement(ProcessingPage)));

    await waitFor(() => {
      expect(screen.getByText(/无法加载工具配置/)).toBeTruthy();
    });
  });

  it("initializes tool toggles from API data", async () => {
    vi.mocked(client.fetchProcessingTools).mockResolvedValue({
      tools: [
        { id: "tool_a", label: "解析器A", description: "", enabled: true },
        { id: "tool_b", label: "脱敏工具B", description: "", enabled: false },
      ],
      use_hybrid_expert_router: true,
    });

    render(wrapper(React.createElement(ProcessingPage)));

    // Wait for the LLM router toggle text to appear
    await waitFor(() => {
      expect(screen.getByText("启用大模型选工具（LangChain bind_tools）")).toBeTruthy();
    });

    // Verify tool labels appear
    expect(screen.getByText("解析器A")).toBeTruthy();
    expect(screen.getByText("脱敏工具B")).toBeTruthy();
  });

  it("renders extension map details section", async () => {
    vi.mocked(client.fetchProcessingTools).mockResolvedValue({
      tools: [{ id: "t1", label: "工具1", description: "", enabled: true }],
      use_hybrid_expert_router: false,
    });

    render(wrapper(React.createElement(ProcessingPage)));

    await waitFor(() => {
      expect(screen.getByText("工具1")).toBeTruthy();
    });

    // Extension map summary should be present
    expect(screen.getByText("扩展名 → 解析工具（只读）")).toBeTruthy();
  });
});
