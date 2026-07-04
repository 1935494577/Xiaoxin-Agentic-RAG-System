/**
 * RequireAuth route guard tests.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import "@testing-library/jest-dom/vitest";
import { AuthProvider } from "../src/context/AuthContext";
import { RequireAuth } from "../src/components/layout/RequireAuth";
import { AUTH_SESSION_KEY } from "../src/lib/constants";

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

function ProtectedPage() {
  return <div>protected-content</div>;
}

function renderGuard(initialPath: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/login" element={<div>login-page</div>} />
          <Route element={<RequireAuth />}>
            <Route path="/admin/ingest" element={<ProtectedPage />} />
            <Route path="/chat" element={<ProtectedPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("RequireAuth", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it("redirects unauthenticated users to login with return path", () => {
    renderGuard("/admin/ingest");
    expect(screen.getByText("login-page")).toBeInTheDocument();
    expect(screen.queryByText("protected-content")).not.toBeInTheDocument();
  });

  it("allows authenticated users to access protected routes", () => {
    localStorageMock.getItem.mockImplementation((key: string) => {
      if (key === AUTH_SESSION_KEY) {
        return JSON.stringify({
          username: "alice",
          department: "技术部",
          role: "admin",
          token: "tok_test",
          userId: "u_alice",
          loggedInAt: Date.now(),
        });
      }
      return null;
    });

    renderGuard("/admin/ingest");
    expect(screen.getByText("protected-content")).toBeInTheDocument();
    expect(screen.queryByText("login-page")).not.toBeInTheDocument();
  });
});
