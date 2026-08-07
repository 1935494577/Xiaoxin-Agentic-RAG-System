/**
 * AppShell — P3 移动端导航抽屉。
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

vi.mock("../src/context/UserProfileContext", () => ({
  UserProfileProvider: ({ children }: { children: React.ReactNode }) => children,
  useUserProfile: () => ({
    loading: false,
    displayName: "测试用户",
    avatarUrl: "",
    aiDisplayName: "",
    aiAvatarUrl: "",
    department: "运营部",
    saveProfile: vi.fn(),
  }),
}));

vi.mock("../src/hooks/useAuth", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    department: "运营部",
    username: "测试用户",
    role: "operator",
    logout: vi.fn(),
  }),
}));

vi.mock("../src/components/layout/SidebarUserProfile", () => ({
  SidebarUserProfile: () => <div data-testid="sidebar-profile">profile</div>,
}));

import { AppShell } from "../src/components/layout/AppShell";

function renderShell() {
  return render(
    React.createElement(
      MemoryRouter,
      { initialEntries: ["/chat"] },
      React.createElement(
        Routes,
        null,
        React.createElement(
          Route,
          { element: React.createElement(AppShell) },
          React.createElement(Route, { path: "/chat", element: React.createElement("div", null, "聊天页") })
        )
      )
    )
  );
}

describe("AppShell mobile drawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders mobile menu button", () => {
    renderShell();
    expect(screen.getByRole("button", { name: "打开导航" })).toBeTruthy();
  });

  it("opens navigation drawer on menu click", () => {
    renderShell();
    expect(screen.queryByRole("dialog", { name: "导航菜单" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "打开导航" }));
    expect(screen.getByRole("dialog", { name: "导航菜单" })).toBeTruthy();
  });

  it("closes drawer when overlay clicked", () => {
    renderShell();
    fireEvent.click(screen.getByRole("button", { name: "打开导航" }));
    const dialog = screen.getByRole("dialog", { name: "导航菜单" });
    const overlay = dialog.querySelector(".animate-dialog-overlay") as HTMLElement;
    fireEvent.click(overlay);
    expect(screen.queryByRole("dialog", { name: "导航菜单" })).toBeNull();
  });

  it("closes drawer after clicking a nav item", () => {
    renderShell();
    fireEvent.click(screen.getByRole("button", { name: "打开导航" }));
    const dialog = screen.getByRole("dialog", { name: "导航菜单" });
    const navLink = dialog.querySelector("a");
    expect(navLink).toBeTruthy();
    fireEvent.click(navLink as HTMLElement);
    expect(screen.queryByRole("dialog", { name: "导航菜单" })).toBeNull();
  });

  it("desktop sidebar container hidden on mobile (responsive classes)", () => {
    const { container } = renderShell();
    const desktopWrap = container.querySelector(".hidden.md\\:block");
    expect(desktopWrap).toBeTruthy();
  });
});
