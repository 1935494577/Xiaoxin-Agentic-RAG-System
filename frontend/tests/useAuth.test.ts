/**
 * useAuth hook tests.
 * Verifies userId generation, persistence, and stability — critical for session survival.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

import { useAuth } from "../src/hooks/useAuth";

describe("useAuth", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("generates a new userId when none is stored", () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current.userId).toMatch(/^u_[a-z0-9]+$/);
    expect(result.current.userId.length).toBeGreaterThan(6);
  });

  it("returns stored userId when it exists", () => {
    localStorageMock.getItem.mockReturnValueOnce('"u_stored_id_123"');

    const { result } = renderHook(() => useAuth());

    expect(result.current.userId).toBe("u_stored_id_123");
    // Should not overwrite stored value
    expect(localStorageMock.setItem).not.toHaveBeenCalled();
  });

  it("userId is stable across re-renders (referential equality)", () => {
    const { result, rerender } = renderHook(() => useAuth());
    const first = result.current.userId;

    rerender();
    const second = result.current.userId;

    expect(first).toBe(second);
  });

  it("two separate calls return the same stored userId", () => {
    const { result: a } = renderHook(() => useAuth());
    const { result: b } = renderHook(() => useAuth());

    // userId is persisted to localStorage on first call; second call reads it back
    expect(a.current.userId).toBe(b.current.userId);
  });

  it("uses key rag_chat_user_id", () => {
    renderHook(() => useAuth());
    expect(localStorageMock.getItem).toHaveBeenCalledWith("rag_chat_user_id");
  });
});
