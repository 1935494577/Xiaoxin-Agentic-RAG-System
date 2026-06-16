/**

 * LoginPage tests.

 */

import { describe, it, expect, vi, beforeEach } from "vitest";

import { render, screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { MemoryRouter, Route, Routes } from "react-router-dom";

import "@testing-library/jest-dom/vitest";

import LoginPage from "../src/pages/LoginPage";



vi.mock("../src/api/client", () => ({

  saveUserProfile: vi.fn().mockResolvedValue({

    user_id: "u_test",

    display_name: "张三",

    department: "技术部",

    avatar_url: "",

    ai_display_name: "",

    ai_avatar_url: "",

  }),

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

  return render(

    <MemoryRouter initialEntries={[initial]}>

      <Routes>

        <Route path="/login" element={<LoginPage />} />

        <Route path="/admin/ingest" element={<div>Admin Ingest</div>} />

        <Route path="/" element={<div>Chat Home</div>} />

      </Routes>

    </MemoryRouter>

  );

}



describe("LoginPage", () => {

  beforeEach(() => {

    localStorageMock.clear();

    vi.clearAllMocks();

  });



  it("renders login form fields and internal platform messaging", () => {

    renderLogin();

    expect(screen.getByRole("heading", { name: "员工登录" })).toBeInTheDocument();

    expect(screen.getByText(/根据所选部门开放对应功能权限/)).toBeInTheDocument();

    expect(screen.getByText(/不同部门可使用的管理功能/)).toBeInTheDocument();

    expect(screen.getByLabelText("用户名")).toBeInTheDocument();

    expect(screen.getByLabelText("密码")).toBeInTheDocument();

    expect(screen.getByLabelText("所属部门")).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /进入工作台/ })).toBeInTheDocument();

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



    const { saveUserProfile } = await import("../src/api/client");

    expect(saveUserProfile).toHaveBeenCalledWith(

      expect.objectContaining({

        display_name: "张三",

        department: "技术部",

      })

    );

  });



  it("links to anonymous chat", () => {

    renderLogin();

    const link = screen.getByRole("link", { name: "仅体验对话功能" });

    expect(link).toHaveAttribute("href", "/chat");

  });

});


