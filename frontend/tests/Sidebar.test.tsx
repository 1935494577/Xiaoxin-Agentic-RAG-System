import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "../src/components/layout/Sidebar";

vi.mock("../src/context/UserProfileContext", () => ({
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

vi.mock("../src/components/layout/SidebarUserProfile", () => ({
  SidebarUserProfile: () => <div data-testid="sidebar-profile">profile</div>,
}));

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows only department-allowed admin nav for 运营部", () => {
    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText("Jnao Chat")).toBeInTheDocument();
    expect(screen.getByText("数据入库")).toBeInTheDocument();
    expect(screen.getByText("提示词")).toBeInTheDocument();
    expect(screen.getByText("模型")).toBeInTheDocument();

    expect(screen.queryByText("向量库")).not.toBeInTheDocument();
    expect(screen.queryByText("用户反馈")).not.toBeInTheDocument();
  });

  it("renders workspace and admin section labels", () => {
    render(
      <MemoryRouter initialEntries={["/admin/ingest"]}>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText("工作区")).toBeInTheDocument();
    expect(screen.getByText("管理")).toBeInTheDocument();
    expect(screen.getByText("管理后台")).toBeInTheDocument();
  });
});
