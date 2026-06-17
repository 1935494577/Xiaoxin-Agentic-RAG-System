/**
 * useAuth hook tests.
 * Verifies userId generation, persistence, and stability — critical for session survival.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { AuthProvider } from "../src/context/AuthContext";
import { useAuth } from "../src/hooks/useAuth";

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });
Object.defineProperty(window, "sessionStorage", { value: localStorageMock });

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("useAuth", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("generates a new userId when none is stored", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.userId).toMatch(/^u_[a-z0-9]+$/);
    expect(result.current.userId.length).toBeGreaterThan(6);
  });

  it("returns stored userId when it exists", () => {
    localStorageMock.getItem.mockReturnValueOnce('"u_stored_id_123"');

    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.userId).toBe("u_stored_id_123");
    expect(localStorageMock.setItem).not.toHaveBeenCalled();
  });

  it("userId is stable across re-renders (referential equality)", () => {
    const { result, rerender } = renderHook(() => useAuth(), { wrapper });
    const first = result.current.userId;

    rerender();
    const second = result.current.userId;

    expect(first).toBe(second);
  });

  it("two separate calls return the same stored userId", () => {
    const { result: a } = renderHook(() => useAuth(), { wrapper });
    const { result: b } = renderHook(() => useAuth(), { wrapper });

    expect(a.current.userId).toBe(b.current.userId);
  });

  it("uses key rag_chat_user_id", () => {
    renderHook(() => useAuth(), { wrapper });
    expect(localStorageMock.getItem).toHaveBeenCalledWith("rag_chat_user_id");
  });

  it("login stores session and marks authenticated", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(false);

    act(() => {
      result.current.login("alice", "运营部", true);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.username).toBe("alice");
    expect(result.current.department).toBe("运营部");
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "jnao_auth_session",
      expect.stringContaining('"username":"alice"')
    );
  });

  it("logout clears session", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.login("bob", "技术部");
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("jnao_auth_session");
  });

  it("shares session state across hook instances in one provider", () => {
    function useTwoAuth() {
      const a = useAuth();
      const b = useAuth();
      return { a, b };
    }

    const { result } = renderHook(() => useTwoAuth(), { wrapper });

    act(() => {
      result.current.a.login("carol", "媒体部");
    });

    expect(result.current.b.isAuthenticated).toBe(true);
    expect(result.current.b.username).toBe("carol");

    act(() => {
      result.current.b.logout();
    });

    expect(result.current.a.isAuthenticated).toBe(false);
  });
});
