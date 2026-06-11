/**
 * Tests for useSessions hook — data loading, error exposure, refetch on create.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock the API client
vi.mock("../src/api/client", () => ({
  listSessions: vi.fn(),
  createSession: vi.fn(),
  deleteSession: vi.fn(),
}));

import { useSessions } from "../src/hooks/useSessions";
import * as client from "../src/api/client";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe("useSessions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns sessions on successful fetch", async () => {
    const mockSessions = [
      { id: "s1", title: "对话1", updated_at: "2025-01-01" },
      { id: "s2", title: "对话2", updated_at: "2025-01-02" },
    ];
    vi.mocked(client.listSessions).mockResolvedValue(mockSessions);

    const { result } = renderHook(() => useSessions("user1"), { wrapper });

    // Initially loading
    expect(result.current.isLoading).toBe(true);
    expect(result.current.sessions).toEqual([]);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.sessions).toEqual(mockSessions);
    expect(result.current.error).toBeNull();
  });

  it("exposes error when fetch fails", async () => {
    const err = new Error("Network Error");
    vi.mocked(client.listSessions).mockRejectedValue(err);

    const { result } = renderHook(() => useSessions("user1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.sessions).toEqual([]);
    expect(result.current.error).toBeTruthy();
  });

  it("create calls API and refetches session list", async () => {
    const newSession = { id: "new1", title: "新对话", updated_at: "2025-01-03" };
    vi.mocked(client.listSessions).mockResolvedValue([]);
    vi.mocked(client.createSession).mockResolvedValue(newSession);

    const { result } = renderHook(() => useSessions("user1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Before create
    expect(result.current.sessions).toEqual([]);

    // Create session
    let created: Awaited<ReturnType<typeof result.current.create>>;
    await act(async () => {
      created = await result.current.create();
    });

    expect(created!).toEqual(newSession);
    expect(client.createSession).toHaveBeenCalledWith("user1");
    expect(client.listSessions).toHaveBeenCalledTimes(2); // initial + refetch
  });

  it("remove calls deleteSession and refetches", async () => {
    vi.mocked(client.listSessions).mockResolvedValue([{ id: "s1", title: "对话1" }]);
    vi.mocked(client.deleteSession).mockResolvedValue();

    const { result } = renderHook(() => useSessions("user1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.remove("s1");
    });

    expect(client.deleteSession).toHaveBeenCalledWith("user1", "s1");
    expect(client.listSessions).toHaveBeenCalledTimes(2); // initial + refetch after delete
  });

  it("returns empty sessions when userId is empty", async () => {
    vi.mocked(client.listSessions).mockResolvedValue([]);

    const { result } = renderHook(() => useSessions(""), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.sessions).toEqual([]);
    expect(client.listSessions).toHaveBeenCalledWith("");
  });
});
