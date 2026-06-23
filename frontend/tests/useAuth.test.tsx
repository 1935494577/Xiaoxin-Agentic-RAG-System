/**
 * useAuth hook tests — session login via API mock.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { AuthProvider } from "../src/context/AuthContext";
import { useAuth } from "../src/hooks/useAuth";

const authLogin = vi.fn();
const authLogout = vi.fn();

vi.mock("../src/api/client", () => ({
  authLogin: (...args: unknown[]) => authLogin(...args),
  authLogout: (...args: unknown[]) => authLogout(...args),
}));

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
    authLogout.mockResolvedValue(undefined);
  });

  it("starts unauthenticated with empty userId", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.userId).toBe("");
  });

  it("restores session from storage", () => {
    localStorageMock.getItem.mockImplementation((key: string) => {
      if (key === "jnao_auth_session") {
        return JSON.stringify({
          username: "tech1",
          department: "技术部",
          role: "superadmin",
          token: "tok_abc",
          userId: "u_tech1",
          loggedInAt: 1,
        });
      }
      return null;
    });

    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.userId).toBe("u_tech1");
    expect(result.current.username).toBe("tech1");
  });

  it("login stores session from API response", async () => {
    authLogin.mockResolvedValue({
      token: "tok_new",
      user: { id: "u_ops1", username: "ops1", department: "运营部", display_name: "ops1" },
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login("ops1", "secret", true);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.username).toBe("ops1");
    expect(result.current.department).toBe("运营部");
    expect(result.current.userId).toBe("u_ops1");
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      "jnao_auth_session",
      expect.stringContaining('"token":"tok_new"')
    );
  });

  it("logout clears session", async () => {
    authLogin.mockResolvedValue({
      token: "tok",
      user: { id: "u1", username: "bob", department: "技术部", display_name: "bob" },
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login("bob", "pw");
      await result.current.logout();
    });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(false);
    });
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("jnao_auth_session");
  });

  it("shares session state across hook instances in one provider", async () => {
    authLogin.mockResolvedValue({
      token: "tok",
      user: { id: "u2", username: "carol", department: "媒体部", display_name: "carol" },
    });

    function useTwoAuth() {
      const a = useAuth();
      const b = useAuth();
      return { a, b };
    }

    const { result } = renderHook(() => useTwoAuth(), { wrapper });

    await act(async () => {
      await result.current.a.login("carol", "pw");
    });

    expect(result.current.b.isAuthenticated).toBe(true);
    expect(result.current.b.username).toBe("carol");

    await act(async () => {
      await result.current.b.logout();
    });

    expect(result.current.a.isAuthenticated).toBe(false);
  });
});
