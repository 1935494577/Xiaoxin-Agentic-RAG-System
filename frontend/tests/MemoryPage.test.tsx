/**
 * MemoryPage component test.
 * Verifies that the form initializes from uiConfig API data (via useEffect, not render-phase setState).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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
  return React.createElement(QueryClientProvider, { client: qc }, ui);
}

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

  it("initializes form fields from API config", async () => {
    vi.mocked(client.fetchUiConfig).mockResolvedValue({
      max_history_turns: 10,
      max_history_chars: 8000,
      kb_min_score: 0.7,
      kb_min_rerank_score: -0.5,
      stream_fast_mode: false,
      long_term_memory_enabled: true,
      general_fallback_enabled: true,
      kb_llm_judge: false,
      kb_post_stream_fallback: true,
      hybrid_expert_mode: false,
      stream_verifier_enabled: true,
      graph_verifier_enabled: false,
      suggested_questions: ["问题1", "问题2", "问题3"],
    });

    render(wrapper(React.createElement(MemoryPage)));

    await waitFor(() => {
      expect(screen.getByText("对话记忆")).toBeTruthy();
    });

    // Verify suggested questions populated
    const textarea = screen.getByPlaceholderText("每行一个问题") as HTMLTextAreaElement;
    expect(textarea.value).toContain("问题1");
    expect(textarea.value).toContain("问题2");

    // Verify save button exists
    expect(screen.getByText("保存")).toBeTruthy();
  });

  it("renders memory toggle labels", async () => {
    vi.mocked(client.fetchUiConfig).mockResolvedValue({
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
    });

    render(wrapper(React.createElement(MemoryPage)));

    await waitFor(() => {
      expect(screen.getByText("长期记忆（long_term_memory_enabled）")).toBeTruthy();
    });

    expect(screen.getByText("全局通用兜底（general_fallback_enabled）")).toBeTruthy();
    expect(screen.getByText("LLM 相关性判断（kb_llm_judge）")).toBeTruthy();
    expect(screen.getByText("混合专家模式默认开（hybrid_expert_mode）")).toBeTruthy();
  });
});
