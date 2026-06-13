import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import React from "react";

vi.mock("../src/api/client", () => ({
  fetchUiConfig: vi.fn(),
  saveUiConfig: vi.fn(),
}));

import MemoryPage from "../src/pages/admin/MemoryPage";
import * as client from "../src/api/client";

function wrapper(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return React.createElement(
    MemoryRouter,
    null,
    React.createElement(QueryClientProvider, { client: qc }, ui)
  );
}

const baseConfig = {
  max_history_turns: 6,
  max_history_chars: 6000,
  kb_min_score: 0.55,
  kb_min_rerank_score: 0.0,
  stream_fast_mode: true,
  long_term_memory_enabled: true,
  general_fallback_enabled: false,
  kb_llm_judge: true,
  kb_post_stream_fallback: false,
  hybrid_expert_mode: false,
  stream_verifier_enabled: false,
  graph_verifier_enabled: false,
  conversation_condense_enabled: true,
  history_prune_enabled: true,
  chat_routing_tier: "balanced",
};

describe("MemoryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    vi.mocked(client.fetchUiConfig).mockReturnValue(new Promise(() => {}));
    render(wrapper(React.createElement(MemoryPage)));
    expect(screen.getByText("加载中...")).toBeTruthy();
  });

  it("shows error when API fails", async () => {
    vi.mocked(client.fetchUiConfig).mockRejectedValue(new Error("API down"));
    render(wrapper(React.createElement(MemoryPage)));
    await waitFor(() => {
      expect(screen.getByText(/无法加载配置/)).toBeTruthy();
    });
  });

  it("initializes form on basic tab", async () => {
    vi.mocked(client.fetchUiConfig).mockResolvedValue({
      ...baseConfig,
      max_history_turns: 10,
      suggested_questions: ["问题1", "问题2"],
    });

    render(wrapper(React.createElement(MemoryPage)));

    await waitFor(() => {
      expect(screen.getByText("对话设置")).toBeTruthy();
    });

    const textarea = screen.getByPlaceholderText("每行一个问题") as HTMLTextAreaElement;
    expect(textarea.value).toContain("问题1");
    expect(screen.getByText("混合专家模式（新用户默认开启）")).toBeTruthy();
  });

  it("shows KB settings on kb tab", async () => {
    vi.mocked(client.fetchUiConfig).mockResolvedValue(baseConfig);
    render(wrapper(React.createElement(MemoryPage)));

    await waitFor(() => {
      expect(screen.getByText("检索与 KB")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("检索与 KB"));

    await waitFor(() => {
      expect(screen.getByText("LLM 相关性判断")).toBeTruthy();
    });
    expect(screen.getByText("全局通用兜底")).toBeTruthy();
  });

  it("links to models page for routing_model", async () => {
    vi.mocked(client.fetchUiConfig).mockResolvedValue(baseConfig);
    render(wrapper(React.createElement(MemoryPage)));

    await waitFor(() => {
      expect(screen.getByText("性能路由")).toBeTruthy();
    });

    fireEvent.click(screen.getByText("性能路由"));

    await waitFor(() => {
      expect(screen.getByText(/预处理模型（routing_model）/)).toBeTruthy();
    });
    expect(screen.queryByPlaceholderText(/gpt-4o-mini/)).toBeNull();
  });
});
