/**
 * TracePage — P0: skeleton loading + lucide status icons (no emoji).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("../src/api/client", () => ({
  fetchTraceStatus: vi.fn(),
}));

import TracePage from "../src/pages/admin/TracePage";
import * as client from "../src/api/client";

function wrapper(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, ui);
}

describe("TracePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows skeleton while loading", () => {
    vi.mocked(client.fetchTraceStatus).mockReturnValue(new Promise(() => {}));
    render(wrapper(React.createElement(TracePage)));
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
  });

  it("renders lucide status icons instead of emoji", async () => {
    vi.mocked(client.fetchTraceStatus).mockResolvedValue({
      backend: "local_jsonl",
      local_enabled: true,
      local_path: "data/chat_trace.jsonl",
      local_file_exists: true,
      local_record_count: 3,
      active: true,
      hints: [],
      langfuse_enabled: false,
      langfuse_tracing: true,
      langfuse_configured: false,
      langfuse_package_installed: true,
      langfuse_host: "https://cloud.langfuse.com",
    });
    const { container } = render(wrapper(React.createElement(TracePage)));

    await waitFor(() => {
      expect(screen.getByText("Langfuse 检查项")).toBeTruthy();
    });
    expect(container.textContent).not.toContain("✅");
    expect(container.textContent).not.toContain("⬜");
    // lucide renders svg icons
    expect(container.querySelectorAll("svg").length).toBeGreaterThan(0);
  });
});
