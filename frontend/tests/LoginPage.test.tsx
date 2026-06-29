/**
 * LoginPage tests.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@testing-library/jest-dom/vitest";
import LoginPage from "../src/pages/LoginPage";
import { AuthProvider } from "../src/context/AuthContext";

const authLogin = vi.fn();
const authMe = vi.fn();

vi.mock("../src/api/client", () => ({
  authLogin: (...args: unknown[]) => authLogin(...args),
  authLogout: vi.fn(),
  authMe: (...args: unknown[]) => authMe(...args),
  mergeLegacyUserProfile: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
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

function renderLogin(initial = "/login") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initial]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/admin/ingest" element={<div>Admin Ingest</div>} />
            <Route path="/" element={<div>Chat Home</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    authMe.mockRejectedValue(new Error("offline"));
    authLogin.mockResolvedValue({
      token: "tok",
      user: {
        id: "u_test",
        username: "张三",
        department: "技术部",
        display_name: "张三",
      },
    });
  });

  it("renders login form fields", () => {
    renderLogin();

    expect(screen.getByRole("heading", { name: "员工登录" })).toBeInTheDocument();
    expect(screen.getByLabelText("用户名")).toBeInTheDocument();
    expect(screen.getByLabelText("密码")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /进入工作台/ })).toBeInTheDocument();
    expect(screen.queryByLabelText("所属部门")).not.toBeInTheDocument();
  });

  it("shows validation when username is empty", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("button", { name: /进入工作台/ }));

    const { toast } = await import("sonner");
    expect(toast.error).toHaveBeenCalledWith("请输入用户名");
  });

  it("submits and navigates to return path", async () => {
    const user = userEvent.setup();
    renderLogin("/login?from=%2Fadmin%2Fingest");

    await user.type(screen.getByLabelText("用户名"), "张三");
    await user.type(screen.getByLabelText("密码"), "secret");
    await user.click(screen.getByRole("button", { name: /进入工作台/ }));

    await waitFor(() => {
      expect(screen.getByText("Admin Ingest")).toBeInTheDocument();
    });

    expect(authLogin).toHaveBeenCalledWith("张三", "secret", true);
  });

  it("does not offer anonymous chat without login", () => {
    renderLogin();
    expect(screen.queryByRole("link", { name: "仅体验对话功能" })).not.toBeInTheDocument();
  });
});
